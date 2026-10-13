// DOM behaviour: word reveals, chapter rail, hover highlights, countdown,
// sound toggle and the loader. Everything here works without WebGL too.
export function setupUI(sections) {
  // Split headings into words so they can rise in one by one.
  document.querySelectorAll('.split').forEach((el) => {
    const words = el.textContent.trim().split(/\s+/)
    el.setAttribute('aria-label', el.textContent.trim())
    el.textContent = ''
    words.forEach((word, i) => {
      const outer = document.createElement('span')
      outer.className = 'w'
      outer.setAttribute('aria-hidden', 'true')
      const inner = document.createElement('span')
      inner.textContent = word
      inner.style.transitionDelay = `${i * 55}ms`
      outer.append(inner)
      el.append(outer, ' ')
    })
  })

  const seen = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in')
          seen.unobserve(entry.target)
        }
      }
    },
    { threshold: 0.2, rootMargin: '0px 0px -8% 0px' },
  )
  document.querySelectorAll('.split, .reveal').forEach((el) => seen.observe(el))

  // Chapter rail.
  const rail = document.getElementById('rail')
  const railItems = sections.map((section, k) => {
    const li = document.createElement('li')
    const btn = document.createElement('button')
    btn.type = 'button'
    btn.innerHTML = `<span class="rail-num">${section.dataset.num ?? ''}</span><span class="rail-label">${section.dataset.label}</span>`
    btn.addEventListener('click', () => goTo(section))
    li.append(btn)
    rail.append(li)
    return li
  })
  const railTitle = document.getElementById('rail-title')

  let goTo = (el) => el.scrollIntoView({ behavior: 'smooth' })
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    const id = a.getAttribute('href').slice(1)
    const target = id && document.getElementById(id)
    if (!target) return
    a.addEventListener('click', (e) => {
      e.preventDefault()
      goTo(target)
    })
  })

  // Hover or focus an item with data-hl to light up its group in the sculpture.
  let current = null
  document.querySelectorAll('[data-hl]').forEach((el) => {
    const section = sections.indexOf(el.closest('[data-scene]'))
    const on = () => {
      current = { group: Number(el.dataset.hl), section }
      el.classList.add('is-lit')
    }
    const off = () => {
      if (current?.group === Number(el.dataset.hl)) current = null
      el.classList.remove('is-lit')
    }
    el.addEventListener('pointerenter', on)
    el.addEventListener('pointerleave', off)
    el.addEventListener('focus', on)
    el.addEventListener('blur', off)
  })

  // Five minutes on stage: a real countdown while the chapter is visible.
  document.querySelectorAll('[data-countdown]').forEach((el) => {
    let timer
    let left = 300
    const draw = () => {
      el.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`
    }
    new IntersectionObserver(([entry]) => {
      clearInterval(timer)
      if (entry.isIntersecting) {
        timer = setInterval(() => {
          left = left > 0 ? left - 1 : 300
          draw()
        }, 1000)
      } else {
        left = 300
        draw()
      }
    }).observe(el)
  })

  // Registration is not open yet, so the button explains when it opens.
  document.querySelectorAll('[data-register]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const note = btn.parentElement.querySelector('.register-note')
      if (note) note.hidden = false
    })
  })

  const soundBtn = document.getElementById('sound')
  const marquees = [...document.querySelectorAll('.marquee')]
  const loader = document.getElementById('loader')
  let lastIndex = -1

  return {
    ready() {
      document.documentElement.classList.add('is-ready')
      setTimeout(() => loader?.remove(), 1200)
    },
    bindScroll(fn) {
      goTo = fn
    },
    highlight() {
      return current
    },
    onSound(fn) {
      soundBtn.addEventListener('click', async () => {
        const playing = await fn()
        soundBtn.setAttribute('aria-pressed', String(playing))
        soundBtn.querySelector('.sound-state').textContent = playing ? 'On' : 'Off'
      })
    },
    update(t, velocity) {
      const index = Math.round(t)
      if (index !== lastIndex) {
        railItems.forEach((li, k) => li.classList.toggle('is-current', k === index))
        railTitle.textContent = sections[index]?.dataset.label ?? ''
        document.documentElement.classList.toggle('past-hero', index > 0)
        lastIndex = index
      }
      const skew = Math.max(-8, Math.min(8, velocity * 0.25))
      for (const m of marquees) m.style.setProperty('--skew', `${skew}deg`)
    },
  }
}
