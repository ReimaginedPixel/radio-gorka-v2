import { computed, ref } from 'vue'
import { api } from '../lib/api'
import { toast } from './useToast'

// Zgłoszenia z tej przeglądarki. Ticket pozwala sprawdzić status i wycofać zgłoszenie.
const KEY = 'rg-requests'
const DONE = ['played', 'cancelled', 'removed']

function load() {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(parsed) ? parsed.filter((r) => r && r.id && r.ticket) : []
  } catch {
    return []
  }
}

const requests = ref(load())

function save() {
  try {
    localStorage.setItem(
      KEY,
      JSON.stringify(requests.value.map(({ landing, ...rest }) => rest)),
    )
  } catch {
    // brak localStorage: lista żyje do odświeżenia strony
  }
}

function add(request) {
  requests.value = [{ ...request, landing: true }, ...requests.value.filter((r) => r.id !== request.id)]
  save()
}

function land(id) {
  requests.value = requests.value.map((r) => (r.id === id ? { ...r, landing: false } : r))
}

function forget(id) {
  requests.value = requests.value.filter((r) => r.id !== id)
  save()
}

async function cancel(request) {
  await api.cancel(request.id, request.ticket)
  forget(request.id)
}

async function refresh() {
  const tracked = requests.value.filter((r) => !DONE.includes(r.status))
  if (!tracked.length) return
  const { requests: fresh } = await api.lookup(tracked.map(({ id, ticket }) => ({ id, ticket })))
  const byId = new Map(fresh.map((r) => [r.id, r]))

  const next = []
  for (const old of requests.value) {
    const now = byId.get(old.id)
    if (!now) {
      // serwer nie zna już tego zgłoszenia (np. inna baza), zostawiamy tylko odrzucone do zamknięcia
      if (old.status === 'rejected') next.push(old)
      continue
    }
    if (now.status !== old.status || now.nowPlaying !== old.nowPlaying) {
      if (now.nowPlaying && !old.nowPlaying) toast(`Teraz gra Twój utwór: ${now.title}`)
      else if (now.status === 'accepted' && old.status === 'pending') toast(`Zaakceptowane: ${now.title}`)
      else if (now.status === 'rejected' && old.status !== 'rejected') toast(`Odrzucone: ${now.title}`, 'error')
    }
    if (DONE.includes(now.status)) continue
    // tytuł, wykonawca i okładka z wyszukiwarki są dokładniejsze niż te z serwera
    next.push({ ...old, ...now, title: old.title, artist: old.artist, thumbnail: old.thumbnail, ticket: old.ticket, landing: old.landing })
  }
  requests.value = next
  save()
}

export function useMyRequests() {
  const ids = computed(() => new Set(requests.value.map((r) => r.id)))
  return { requests, ids, add, land, forget, cancel, refresh }
}
