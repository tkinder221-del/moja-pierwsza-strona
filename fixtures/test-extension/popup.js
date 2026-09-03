chrome.storage.local.get('fixtureSeen').then(({ fixtureSeen }) => {
  document.getElementById('state').textContent = fixtureSeen ? 'seen' : 'not-seen'
})
