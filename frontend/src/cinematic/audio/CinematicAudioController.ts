type Cue = "signal" | "fracture" | "awakening" | "forge" | "recognition";

export class CinematicAudioController {
  private context: AudioContext | null = null;
  private master: GainNode | null = null;
  private timers = new Set<number>();

  async enable() {
    if (!this.context) {
      this.context = new AudioContext();
      this.master = this.context.createGain();
      this.master.gain.value = 0.13;
      this.master.connect(this.context.destination);
    }
    await this.context.resume();
  }

  cue(name: Cue) {
    if (!this.context || !this.master || this.context.state !== "running")
      return;
    const frequencies: Record<Cue, [number, number]> = {
      signal: [92, 184],
      fracture: [66, 310],
      awakening: [110, 220],
      forge: [48, 144],
      recognition: [73.4, 146.8],
    };
    const now = this.context.currentTime,
      [low, high] = frequencies[name];
    const oscillator = this.context.createOscillator(),
      gain = this.context.createGain(),
      filter = this.context.createBiquadFilter();
    oscillator.type = name === "fracture" ? "sawtooth" : "sine";
    oscillator.frequency.setValueAtTime(low, now);
    oscillator.frequency.exponentialRampToValueAtTime(high, now + 0.7);
    filter.type = "lowpass";
    filter.frequency.value = name === "fracture" ? 900 : 420;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.16, now + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.2);
    oscillator.connect(filter).connect(gain).connect(this.master);
    oscillator.start(now);
    oscillator.stop(now + 1.25);
  }

  mute(muted: boolean) {
    if (this.master && this.context)
      this.master.gain.setTargetAtTime(
        muted ? 0 : 0.13,
        this.context.currentTime,
        0.03,
      );
  }
  dispose() {
    this.timers.forEach(clearTimeout);
    this.timers.clear();
    void this.context?.close();
    this.context = null;
    this.master = null;
  }
}
