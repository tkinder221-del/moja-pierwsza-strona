chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message !== 'fixture-ping') return false
  chrome.storage.local.set({ fixtureSeen: true }).then(() => {
    sendResponse({ reply: 'fixture-pong' })
  })
  return true
})
