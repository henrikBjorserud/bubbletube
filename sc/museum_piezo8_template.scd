// museum_piezo8_template.scd
// Headless starter for 8 piezos -> multichannel interface -> SC FX -> stereo out.

// Choose output device (adjust later)
// Server.default.options.device = "HDMI";
Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

// If you need to pick sample rate / block size later:
// Server.default.options.sampleRate = 48000;
// Server.default.options.blockSize = 512;

s.waitForBoot {
    "BOOT OK - starting piezo8 template".postln;

    SynthDef(\piezo8, {
        var in, gains, sum, cleaned, wet, out;
        var dryWet, outGain;

        // ----- Controls you tweak later -----
        gains  = \gains.kr([1,1,1,1,1,1,1,1]); // per-input gain
        dryWet = \dryWet.kr(0.5);             // 0 = dry, 1 = wet
        outGain = \outGain.kr(0.2);           // master output gain (start low)
        // -----------------------------------

        // Read 8 hardware inputs (0..7) - adjust mapping Monday if needed
        in = Array.fill(8, { |i| SoundIn.ar(i + 12) }) * gains;

        // Piezo cleanup:
        // 1) remove low rumble/handling thumps
        cleaned = in.collect { |sig| HPF.ar(sig, 80) };

        // 2) soften harsh piezo highs a bit (adjust freq Monday)
        cleaned = cleaned.collect { |sig| LPF.ar(sig, 8000) };

        // 3) tame spikes but keep quiet touches audible
        cleaned = cleaned.collect { |sig|
            Compander.ar(sig, sig, 0.25, 1, 0.2, 0.003, 0.15)
        };

        // Sum to mono for FX stage. comment out below one and use the other when testing.
        sum = Mix(cleaned);
	// sum = cleaned[0]; // try 0..7 to find the right channel

        // "Interesting" FX chain:
        // short delay smear + reverb wash
        wet = sum;
        wet = CombC.ar(wet, 0.3, [0.07, 0.11], 2.0).sum * 0.5 + wet;  // subtle stereo-ish smear
        wet = FreeVerb2.ar(wet, wet, mix: 0.35, room: 0.7, damp: 0.4);

        // Crossfade dry/wet
        out = XFade2.ar(sum, wet, (dryWet * 2) - 1);

        // Output stereo
        Out.ar(0, (out * outGain) ! 2);
    }).add;

    // Start synth with conservative gains
    x = Synth(\piezo8, [
        \gains,  [1,1,1,1,1,1,1,1],
        \dryWet, 0.6,
        \outGain, 0.15
    ]);

    "RUNNING: piezo8 synth started".postln;
};

s.boot;
