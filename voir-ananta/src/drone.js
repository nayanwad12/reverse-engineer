// A small synthesized tanpura: four strings plucked Pa, Sa, Sa, low Sa on loop.
// Starts only from a user gesture (browsers block autoplaying audio).
export function createDrone(onPluck) {
  let ctx
  let master
  let timer
  let next = 0
  let step = 0
  const SA = 138.59 // C#3
  const STRINGS = [SA * 0.75, SA, SA, SA / 2]
  const GAP = 0.95

  function init() {
    ctx = new (window.AudioContext || window.webkitAudioContext)()
    master = ctx.createGain()
    master.gain.value = 0.0
    const delay = ctx.createDelay(1)
    delay.delayTime.value = 0.37
    const feedback = ctx.createGain()
    feedback.gain.value = 0.38
    const wet = ctx.createGain()
    wet.gain.value = 0.35
    master.connect(ctx.destination)
    master.connect(delay)
    delay.connect(feedback)
    feedback.connect(delay)
    delay.connect(wet)
    wet.connect(ctx.destination)
  }

  function pluck(freq, when) {
    const env = ctx.createGain()
    env.gain.setValueAtTime(0, when)
    env.gain.linearRampToValueAtTime(0.2, when + 0.012)
    env.gain.exponentialRampToValueAtTime(0.0006, when + 4.2)
    const tone = ctx.createBiquadFilter()
    tone.type = 'lowpass'
    tone.Q.value = 7
    tone.frequency.setValueAtTime(freq * 16, when)
    tone.frequency.exponentialRampToValueAtTime(freq * 3, when + 2.8)
    for (const [mult, detune, type] of [
      [1, 0, 'sawtooth'],
      [1, 5, 'sawtooth'],
      [2, -4, 'triangle'],
    ]) {
      const osc = ctx.createOscillator()
      osc.type = type
      osc.frequency.value = freq * mult
      osc.detune.value = detune
      osc.connect(tone)
      osc.start(when)
      osc.stop(when + 4.4)
    }
    tone.connect(env)
    env.connect(master)
    setTimeout(onPluck, Math.max(0, (when - ctx.currentTime) * 1000))
  }

  function schedule() {
    while (next < ctx.currentTime + 0.3) {
      pluck(STRINGS[step % 4], next)
      next += GAP * (step % 4 === 3 ? 1.6 : 1)
      step++
    }
  }

  return {
    get playing() {
      return !!timer
    },
    async toggle() {
      if (!ctx) init()
      if (timer) {
        clearInterval(timer)
        timer = null
        master.gain.setTargetAtTime(0, ctx.currentTime, 0.4)
        return false
      }
      await ctx.resume()
      master.gain.setTargetAtTime(0.5, ctx.currentTime, 0.6)
      next = ctx.currentTime + 0.1
      timer = setInterval(schedule, 80)
      schedule()
      return true
    },
  }
}
