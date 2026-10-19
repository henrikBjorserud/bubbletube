// no_thresh_test.scd
// Bypass all threshold gating — pipe raw signal directly into material synthesis.
// If you hear material sounds (wood/harp/brush) when touching piezos:
//   -> threshold levels are wrong for current setup, synthesis chain is fine
// If you hear NOTHING even though passthrough works:
//   -> problem is deeper in synthesis chain

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;
Server.default.options.numWireBufs = 1024;

s.waitForBoot {
    "BOOT OK - no-threshold material test".postln;

    SynthDef(\noThreshMaterials, {
        var ins, gains, outGain;
        var excite, per, sum;

        gains   = [1, 4, 1, 1, 8, 3, 0.2, 1];
        outGain = 1.0;  // much louder than normal

        // Offset 8: correct when Focusrite Control is running
        ins = Array.fill(8, { |i| SoundIn.ar(i + 12) }) * gains;
        ins = ins.collect { |sig| HPF.ar(LPF.ar(sig, 9000), 80) };

        // NO gate — raw rectified signal drives synthesis directly
        excite = ins.collect { |sig| sig.abs };

        per = [
            // piezo 1: WOOD A
            DynKlank.ar(`[ [120, 190, 310, 480], nil, [2.0, 1.5, 1.0, 0.7] ], excite[0]) * 1.0,

            // piezo 2: BRUSH A
            { var n = LPF.ar(HPF.ar(PinkNoise.ar(1.0), 100), 2500) * excite[1].lag(0.2) * 0.4;
              n }.value,

            // piezo 3: HARP A
            ( Ringz.ar(excite[2], 329, 1.5) * 0.5
            + Ringz.ar(excite[2], 494, 1.2) * 0.4
            + Ringz.ar(excite[2], 659, 0.9) * 0.3
            + Ringz.ar(excite[2], 988, 0.7) * 0.2 ),

            // piezo 4: HARP B
            ( Ringz.ar(excite[3], 523, 1.5) * 0.5
            + Ringz.ar(excite[3], 784, 1.2) * 0.4
            + Ringz.ar(excite[3], 1047, 0.9) * 0.3
            + Ringz.ar(excite[3], 1568, 0.7) * 0.2 ),

            // piezo 5: BRUSH B
            { var n = LPF.ar(HPF.ar(PinkNoise.ar(1.0), 40), 400) * excite[4].lag(0.3) * 1.0;
              n }.value,

            // piezo 6: WOOD B
            { var n = LPF.ar(PinkNoise.ar(1.0), 800) * excite[5].lag(0.15) * 0.3;
              DynKlank.ar(`[ [200, 320, 500, 780], nil, [1.5, 1.2, 0.8, 0.5] ], n) * 1.5 }.value,

            // piezo 7: METAL
            DynKlank.ar(`[ [520, 830, 1350, 2100], nil, [0.8, 0.6, 0.5, 0.4] ], excite[6]) * 0.7,

            // piezo 8: WOOD C
            { var k = DynKlank.ar(`[ [280, 420, 680, 1050], nil, [1.0, 0.8, 0.6, 0.4] ], excite[7]) * 1.1;
              k + CombL.ar(k, 1.0, 0.35, 2.5) * 0.5 + CombL.ar(k, 1.0, 0.52, 2.0) * 0.3 }.value,
        ];

        sum = Mix(per);
        sum = Limiter.ar(sum, 0.9);

        Out.ar(0, (sum * outGain) ! 2);
    }).add;

    s.sync;
    x = Synth(\noThreshMaterials);
    "RUNNING: touch each piezo — you should hear its material sound".postln;
    "1=WoodA 2=BrushA 3=HarpA 4=HarpB 5=BrushB 6=WoodB 7=Metal 8=WoodC".postln;
};

s.boot;
