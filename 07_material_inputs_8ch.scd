// 07_material_inputs_8ch.scd
// 8 piezos -> individual materials -> stereo out
// Piezo map: 1=WoodA 2=BrushA 3=HarpA 4=HarpB 5=BrushB 6=WoodB 7=Metal 8=WoodC

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;
Server.default.options.numWireBufs = 1024;

s.waitForBoot {
    "BOOT OK - 8ch material inputs".postln;

    SynthDef(\materials8inputs, {
        var ins, gains, thresh, outGain, dryWet;
        var envs, excite, per, sum;

        gains   = \gains.kr([1, 2, 1, 1, 2, 3, 2.0, 1]); // ch2 BrushA: 4->2, ch5 BrushB: 8->2
        // per-piezo thresholds: 1=WoodA 2=BrushA 3=HarpA 4=HarpB 5=BrushB 6=WoodB 7=Metal 8=WoodC
        thresh  = \thresh.kr([0.05, 0.4, 0.05, 0.05, 0.05, 0.01, 0.01, 0.4]);
        dryWet  = \dryWet.kr(0.7);             // 0=raw 1=material
        outGain = \outGain.kr(0.12);            // master out (start low)

        // Read 8 ADAT inputs (offset 12: analog 1-4 + SPDIF + loopback occupy ch0-11)
        ins = Array.fill(8, { |i| SoundIn.ar(i + 12) }) * gains;
        ins = ins.collect { |sig| HPF.ar(LPF.ar(sig, 9000), 80) };

        // Touch energy per channel
        envs = ins.collect { |sig| Amplitude.kr(sig, 0.002, 0.10) };

        // Excitation: rectified audio gated by threshold
        excite = Array.fill(8, { |i|
            var gate = LagUD.kr(envs[i] > thresh[i], 0.002, 0.15);
            ins[i].abs * gate
        });

        per = [
            // piezo 1: WOOD A - low thick plank
            DynKlank.ar(`[ [120, 190, 310, 480], nil, [2.0, 1.5, 1.0, 0.7] ], excite[0]) * 1.0,

            // piezo 2: BRUSH A - soft warm wind swell
            { var gate = LagUD.kr(envs[1] > thresh[1], 0.05, 1.2);
              var n = LPF.ar(HPF.ar(PinkNoise.ar(1.0), 100), 2500) * gate * 0.4;
              n }.value,

            // piezo 3: HARP A - lower register (E4 B4 E5 B5)
            ( Ringz.ar(excite[2], 329, 1.5) * 0.5
            + Ringz.ar(excite[2], 494, 1.2) * 0.4
            + Ringz.ar(excite[2], 659, 0.9) * 0.3
            + Ringz.ar(excite[2], 988, 0.7) * 0.2 ),

            // piezo 4: HARP B - higher register (C5 G5 C6 G6)
            ( Ringz.ar(excite[3], 523, 1.5) * 0.5
            + Ringz.ar(excite[3], 784, 1.2) * 0.4
            + Ringz.ar(excite[3], 1047, 0.9) * 0.3
            + Ringz.ar(excite[3], 1568, 0.7) * 0.2 ),

            // piezo 5: BRUSH B - low warm brush
            { var gate = LagUD.kr(envs[4] > thresh[4], 0.08, 1.8);
              var n = LPF.ar(HPF.ar(PinkNoise.ar(1.0), 40), 400) * gate * 1.0;
              n }.value,

            // piezo 6: WOOD B - felt hammer drag, kalimba-like
            { var gate = LagUD.kr(envs[5] > thresh[5], 0.06, 1.0);
              var n = LPF.ar(PinkNoise.ar(1.0), 800) * gate * 0.3;
              DynKlank.ar(`[ [200, 320, 500, 780], nil, [1.5, 1.2, 0.8, 0.5] ], n) * 1.5 }.value,

            // piezo 7: METAL - inharmonic, long ring
            DynKlank.ar(`[ [520, 830, 1350, 2100], nil, [0.8, 0.6, 0.5, 0.4] ], excite[6]) * 0.7,

            // piezo 8: WOOD C - higher mallet-like with echo
            { var k = DynKlank.ar(`[ [280, 420, 680, 1050], nil, [1.0, 0.8, 0.6, 0.4] ], excite[7]) * 1.1;
              k + CombL.ar(k, 1.0, 0.35, 0.8) * 0.5 + CombL.ar(k, 1.0, 0.52, 0.6) * 0.3 }.value,
        ];

        // Blend raw with material, limiter per channel
        per = per.collect { |mat, i|
            Limiter.ar(XFade2.ar(ins[i], mat, (dryWet * 2) - 1), 0.95)
        };

        sum = Mix(per);
        // Compander removed: when sum=0 its control decays to 0 -> div/zero -> NaN -> silence
        sum = Limiter.ar(sum, 0.95);

        Out.ar(0, (sum * outGain) ! 2);
    }).add;

    s.sync;

    x = Synth(\materials8inputs, [
        \gains,   [1, 2, 1, 3, 3, 4, 2.0, 2],
        // ch4-8: lower threshold + higher gain to compensate for weaker piezos
        \thresh,  [0.003, 0.05, 0.003, 0.003, 0.003, 0.003, 0.003, 0.003],
        \dryWet,  1.0,
        \outGain, 0.04
    ]);

    "RUNNING: 1=WoodA 2=BrushA 3=HarpA 4=HarpB 5=BrushB 6=WoodB 7=Metal 8=WoodC".postln;
};

ShutDown.add({ s.quit; });

s.reboot;  // always fresh — ensures numWireBufs=1024 takes effect
