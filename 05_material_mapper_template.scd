// 05_material_mapper_template.scd
// Map each piezo touch to a "material" resonator texture.
// You will tune thresholds/gains Monday.

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "BOOT OK - material mapper".postln;

    SynthDef(\materials8, {
        var ins, envs, excite, per, sum, out;
        var gains, thresh, outGain, dryWet;

        gains = \gains.kr([1,1,1,1,1,1,1,1]);
        thresh = \thresh.kr(0.03);       // touch sensitivity (tune!)
        outGain = \outGain.kr(0.2);
        dryWet = \dryWet.kr(0.6);        // how much "material" vs raw

        // 8 inputs
        ins = Array.fill(8, { |i| SoundIn.ar(i + 12) }) * gains;

        // Basic cleanup for piezos
        ins = ins.collect { |sig| HPF.ar(sig, 80) };
        ins = ins.collect { |sig| LPF.ar(sig, 9000) };

        // Envelope follower per channel to detect touch energy
        envs = ins.collect { |sig|
            Amplitude.kr(sig, 0.002, 0.08)  // fast attack, slower release
        };

        // Excitation signal: rectified + emphasized transients
        excite = ins.collect { |sig|
            (sig.abs).clip(0, 1)
        };

        // Per-channel material processing
        per = Array.fill(8, { |i|
            var e, ex, trig, mat, raw;

            e = envs[i];
            ex = excite[i];
            raw = ins[i];

            // A "touch gate": only open when above threshold
            trig = (e > thresh);

            // Make an envelope for the excited material (no hard clicks)
            ex = ex * LagUD.kr(trig, 0.001, 0.15);

            // Pick a material per channel (edit these mappings as you like)
            mat = Select.ar(i, [

                // 0: METAL - bright, ringing
                DynKlank.ar(`[ [800, 1200, 2000, 3200], nil, [2.5, 2.0, 1.6, 1.2] ], ex) * 0.8,

                // 1: WOOD - boxy, shorter decay
                DynKlank.ar(`[ [180, 260, 420, 650], nil, [1.2, 0.9, 0.7, 0.5] ], ex) * 1.2,

                // 2: GLASS/CERAMIC - high, clean, longer
                DynKlank.ar(`[ [1500, 2400, 3800, 5200], nil, [2.0, 1.8, 1.5, 1.2] ], ex) * 0.6,

                // 3: BRUSH - noisy air + comb shimmer
                (CombC.ar(WhiteNoise.ar(0.08) * ex, 0.2, 0.03, 1.2) + (raw * 0.3)),

                // 4: HOLLOW TUBE - formant-ish
                (BPF.ar(ex, 500, 0.2) + BPF.ar(ex, 900, 0.15) + BPF.ar(ex, 1400, 0.12)) * 0.9,

                // 5: RUBBER/SOFT - dull thump + short room
                FreeVerb.ar(LPF.ar(ex, 800) * 0.8, mix: 0.35, room: 0.3, damp: 0.8),

                // 6: STRINGY - resonant comb
                CombL.ar(ex, 0.15, [0.02, 0.027].mean, 2.0) * 0.6,

                // 7: RAW+SPARKLE - mostly real sound with a little sparkle
                (raw * 0.8) + (Ringz.ar(ex, 2400, 0.7) * 0.25)
            ]);

            // Blend raw touch and materialized version
            XFade2.ar(raw, mat, (dryWet * 2) - 1);
        });

        // Sum and output
        sum = Mix(per);
        sum = Compander.ar(sum, sum, 0.3, 1, 0.25, 0.005, 0.2);
        Out.ar(0, (sum * outGain) ! 2);
    }).add;

    x = Synth(\materials8, [
        \gains,   [1,1,1,1,1,1,1,1],
        \thresh,  0.03,
        \dryWet,  0.7,
        \outGain, 0.15
    ]);

    "RUNNING: touch materials, tune \\thresh and \\gains".postln;
};

s.boot;
