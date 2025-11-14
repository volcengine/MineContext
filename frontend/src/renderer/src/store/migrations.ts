import { getLogger } from '@shared/logger/renderer'
import { omit } from 'lodash'

const logger = getLogger('migrations')

const migrations = {
  2: (state: any): any => {
    logger.info('Running redux-persist migration for version 2...')

    if (!state) {
      logger.warn('Migration v2: Received undefined state, returning state as-is.')
      return state
    }

    const newState = omit(state, ['chatHistory'])

    if (state.chatHistory) {
      logger.info('Migration v2: Removed "chatHistory" from persisted state.')
    } else {
      logger.info('Migration v2: "chatHistory" not found in state, nothing to remove.')
    }

    return newState
  }
}
export { migrations }
