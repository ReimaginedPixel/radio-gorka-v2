import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://frog02-20689.wykr.es/api',
})

const VOTER_KEY = 'voter_token'
const VOTER_PREV_KEY = 'voter_token_prev'

// Endpointy, które nie potrzebują sesji przeglądarki ucznia.
const NO_VOTER = /^\/(admin|login|clear-playlist|board|session)/

const readStorage = (key) => {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

const writeStorage = (key, value) => {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    // tryb prywatny lub zablokowany storage: sesja będzie tylko w pamięci
  }
}

let memoryVoterToken = null
let pendingSession = null

export const ensureVoterToken = async () => {
  const existing = readStorage(VOTER_KEY) || memoryVoterToken
  if (existing) return existing
  if (!pendingSession) {
    pendingSession = api
      .post('/session')
      .then((res) => {
        memoryVoterToken = res.data.token
        writeStorage(VOTER_KEY, res.data.token)
        return res.data.token
      })
      .finally(() => {
        pendingSession = null
      })
  }
  return pendingSession
}

const resetVoterToken = () => {
  memoryVoterToken = null
  writeStorage(VOTER_KEY, null)
}

// Po zalogowaniu przez Górkę zapamiętujemy poprzednią sesję, żeby wylogowanie
// na wspólnym komputerze w pokoju przywróciło sesję stanowiska.
export const switchToAccount = (token) => {
  writeStorage(VOTER_PREV_KEY, readStorage(VOTER_KEY))
  memoryVoterToken = token
  writeStorage(VOTER_KEY, token)
}

export const leaveAccount = () => {
  const previous = readStorage(VOTER_PREV_KEY)
  writeStorage(VOTER_PREV_KEY, null)
  if (previous) {
    memoryVoterToken = previous
    writeStorage(VOTER_KEY, previous)
  } else {
    resetVoterToken()
  }
}

api.interceptors.request.use(async (config) => {
  const token = readStorage('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (!NO_VOTER.test(config.url || '')) {
    config.headers['X-Voter-Token'] = await ensureVoterToken()
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config
    // Wygasła lub nieznana sesja ucznia: zakładamy nową i ponawiamy raz.
    if (error.response?.status === 401 && config && !config._voterRetry && !NO_VOTER.test(config.url || '')) {
      config._voterRetry = true
      resetVoterToken()
      return api(config)
    }
    return Promise.reject(error)
  },
)

export const errorMessage = (error, fallback) => error.response?.data?.detail || fallback

export default api
