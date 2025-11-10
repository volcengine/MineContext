import { createSlice, PayloadAction } from '@reduxjs/toolkit'
const initialState = {
  chatHistoryMessages: [] as any[]
}
const chatHistorySlice = createSlice({
  name: 'chatHistory',
  initialState,
  reducers: {
    setChatHistoryMessages(state, action: PayloadAction<any[]>) {
      state.chatHistoryMessages = action.payload
    }
  }
})

export const { setChatHistoryMessages } = chatHistorySlice.actions

export default chatHistorySlice.reducer
