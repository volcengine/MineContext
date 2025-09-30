# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenContext module: generation_report
"""

import datetime, json
from typing import Dict, List, Any, Optional

from opencontext.config import GlobalConfig
from opencontext.storage.global_storage import get_storage
from opencontext.llm.global_vlm_client import generate_with_messages_async
from opencontext.config.global_config import get_prompt_manager
from opencontext.tools.tool_definitions import ALL_TOOL_DEFINITIONS
from opencontext.tools.tools_executor import ToolsExecutor
from opencontext.utils.logging_utils import get_logger
from opencontext.models.enums import ContextType

logger = get_logger(__name__)

class ReportGenerator:
    """
    Context consumer - directly retrieves context from the database, calls the large model to generate results, and supports tool calls to obtain background information.
    """
    
    def __init__(self):
        self.tools_executor = ToolsExecutor()
    
    @property
    def prompt_manager(self):
        return get_prompt_manager()    

    @property
    def storage(self):
        """Get storage from the global singleton."""
        return get_storage()
    
    async def generate_report(self, start_time: int, end_time: int) -> str:
        """
        Generate an activity report for a specified time range.
        
        Args:
            start_time: The start time as a Unix timestamp in seconds.
            end_time: The end time as a Unix timestamp in seconds.
            
        Returns:
            str: The activity report in Markdown format.
        """
        try:
            # Calculate the time range in hours
            time_range_hours = (end_time - start_time) / 3600
            
            # If the time range exceeds 1 hour, use chunked processing
            result = None
            if time_range_hours > 1:
                result = await self._generate_chunked_report(start_time, end_time)
            else:
                result = await self._generate_single_report(start_time, end_time)
            if not result:
                return result

            from opencontext.managers.event_manager import EventType, publish_event
            from opencontext.storage.global_storage import get_storage
            from opencontext.models.enums import VaultType
            now = datetime.datetime.now()
            report_id = get_storage().insert_vaults(
                title=f"Daily Report - {now.strftime('%Y-%m-%d')}",
                summary="",
                content=result,
                document_type=VaultType.DAILY_REPORT.value
            )
            publish_event(
                event_type=EventType.DAILY_SUMMARY_GENERATED,
                data={
                    "doc_id": str(report_id),
                    "doc_type": "vaults",
                    "title": f"Daily Report - {now.strftime('%Y-%m-%d')}",
                    "content": result
                }
            )
            return result
        except Exception as e:
            logger.exception(f"Error generating activity report: {e}")
            return f"Error generating activity report: {str(e)}"
    
    async def _generate_single_report(self, start_time: int, end_time: int) -> str:
        """
        Generate an activity report for a single time period.
        """
        # 1. Directly get context from the database
        contexts = self._get_contexts_from_db(start_time, end_time)
        
        if not contexts:
            return f"No activity records found in the specified time range.\n\nTime range: {self._format_timestamp(start_time)} to {self._format_timestamp(end_time)}"
        
        # 2. Call the large model to generate a daily report, supporting tool calls to get background information
        report = await self._generate_report_with_llm(contexts, start_time, end_time)
        
        return report
    
    async def _generate_chunked_report(self, start_time: int, end_time: int) -> str:
        """
        Generate a chunked activity report (for periods longer than 1 hour), using coroutines for concurrent processing to improve performance.
        """
        logger.info(f"Time range exceeds 1 hour, enabling chunked processing.")
        
        # Segment by hour
        hour_chunks = []
        current_time = start_time
        
        while current_time < end_time:
            chunk_end = min(current_time + 3600, end_time)  # 1-hour chunks
            hour_chunks.append((current_time, chunk_end))
            current_time = chunk_end
        hourly_summaries = await self._process_chunks_concurrently(hour_chunks)
        
        if not hourly_summaries:
            return f"No activity records found in the specified time range.\n\nTime range: {self._format_timestamp(start_time)} to {self._format_timestamp(end_time)}"
        
        # Summarize all hourly reports
        return await self._generate_final_report_from_summaries(hourly_summaries, start_time, end_time)
    
    async def _process_chunks_concurrently(self, hour_chunks: list) -> list:
        """Process all time chunks concurrently."""
        import asyncio
        tasks = []
        for chunk_start, chunk_end in hour_chunks:
            task = self._process_single_chunk_async(chunk_start, chunk_end)
            tasks.append(task)
        semaphore = asyncio.Semaphore(5)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        limited_tasks = [limited_task(task) for task in tasks]
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        hourly_summaries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                chunk_start, chunk_end = hour_chunks[i]
                logger.error(f"Failed to process time chunk {self._format_timestamp(chunk_start)} - {self._format_timestamp(chunk_end)}: {result}")
            elif result:
                hourly_summaries.append(result)
        
        return hourly_summaries
    
    async def _process_single_chunk_async(self, chunk_start: int, chunk_end: int) -> dict:
        """Process a single time chunk asynchronously."""
        contexts = self._get_contexts_from_db(chunk_start, chunk_end)
        if not contexts:
            return None

        summary = await self._generate_hourly_summary(contexts, chunk_start, chunk_end)
        
        if summary:
            return {
                'start_time': chunk_start,
                'end_time': chunk_end,
                'summary': summary
            }
        return None
    
    async def _generate_hourly_summary(self, contexts: List[Dict], start_time: int, end_time: int) -> str:
        """
        Generate an hourly activity summary using a detailed generation_report prompt to provide comprehensive information.
        """
        if not contexts:
            return ""
        try:
            prompt_group = self.prompt_manager.get_prompt_group("generation.generation_report")
            
            start_time_str = self._format_timestamp(start_time)
            end_time_str = self._format_timestamp(end_time)
  
            contexts_str = json.dumps(contexts, ensure_ascii=False, indent=2)
            
            messages = [
                {"role": "system", "content": prompt_group["system"]},
                {"role": "user", "content": prompt_group["user"].format(
                    start_time_str=start_time_str,
                    end_time_str=end_time_str,
                    start_timestamp=start_time,
                    end_timestamp=end_time,
                    contexts=contexts_str
                )}
            ]
            summary = await generate_with_messages_async(messages, enable_executor=False, temperature=0.2)
            return summary
        except Exception as e:
            logger.error(f"Failed to generate hourly summary: {e}")
            return None
    
    async def _generate_final_report_from_summaries(self, hourly_summaries: List[Dict], start_time: int, end_time: int) -> str:
        """
        Generate the final report based on hourly summaries.
        """
        # Build the prompt for the final report
        summaries_text = ""
        for summary_data in hourly_summaries:
            time_str = self._format_timestamp(summary_data['start_time'])
            summaries_text += f"**{time_str}**: {summary_data['summary']}\n\n"
        
        prompt = f"""Please generate a complete activity report based on the following period summaries.

        Time range: {self._format_timestamp(start_time)} to {self._format_timestamp(end_time)}

        Summaries for each period:
        {summaries_text}

        Please generate the final report in the standard format, including sections such as activity overview, core achievements, learning and growth, key associations, and a detailed activity list.
        You can use the search tool to get background information on important entities, but please control the search scope to avoid excessive retrieval."""

        # Get the standard prompt
        prompt_group = self.prompt_manager.get_prompt_group("generation.generation_report")
        system_prompt = prompt_group["system"]
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        report = await generate_with_messages_async(
            messages,
            enable_executor=True,
            tools=ALL_TOOL_DEFINITIONS,
            temperature=0.1,
        )
        return report
    
    def _get_contexts_from_db(self, start_time: int, end_time: int) -> List[Dict]:
        """
        Directly retrieve context information from the database for a specified time range.
        """
        try:
            filters = {}
            if start_time or end_time:
                filters["create_time_ts"] = {}
                if start_time:
                    filters['create_time_ts']['$gte'] = start_time
                if end_time:
                    filters['create_time_ts']['$lte'] = end_time
            
            context_types = [ContextType.ACTIVITY_CONTEXT.value, ContextType.SEMANTIC_CONTEXT.value]
            
            # Get all relevant contexts
            all_contexts = self.storage.get_all_processed_contexts(
                context_types=context_types,
                limit=1000,
                offset=0,
                filter=filters
            )
            
            contexts = []
            for context_type, context_list in all_contexts.items():
                contexts.extend(context_list)
            
            # Sort by time
            contexts.sort(key=lambda x: x.properties.create_time)
            
            # Convert to the format for large model input
            contexts = [context.get_llm_context_string() for context in contexts]
            
            logger.info(f"Retrieved {len(contexts)} context records from the database for the period from {start_time} to {end_time}.")
            return contexts
            
        except Exception as e:
            logger.exception(f"Failed to get context from the database: {e}")
            return []

    async def _generate_report_with_llm(self, contexts: List[Dict], start_time: int, end_time: int) -> str:
        """
        Use a large model to generate an activity report, supporting tool calls to get background information.
        """
        # Get the prompt template
        prompt_group = self.prompt_manager.get_prompt_group("generation.generation_report")
        system_prompt = prompt_group["system"]
        user_prompt_template = prompt_group["user"]
        
        # Format the time strings
        start_time_str = self._format_timestamp(start_time)
        end_time_str = self._format_timestamp(end_time)
        
        # Fill the user prompt template
        user_prompt = user_prompt_template.format(
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            start_timestamp=start_time,
            end_timestamp=end_time,
            contexts=json.dumps(contexts)
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
        report = await generate_with_messages_async(
            messages, 
            enable_executor=True,
            tools=ALL_TOOL_DEFINITIONS,
            temperature=0.1,
        )
        return report
    
    
    def _format_timestamp(self, timestamp: int) -> str:
        """
        Format a timestamp into a readable string.
        """
        try:
            if timestamp:
                dt = datetime.datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return "Unknown time"
        except (ValueError, OSError):
            return "Invalid time"