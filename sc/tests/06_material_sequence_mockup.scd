// 06_material_sequence_mockup.scd
// Plays 8 resonator "materials" sequentially. Headless-safe.
// Stop with Ctrl+C.

Server.default.options.device = "Scarlett 18i8 USB";

~run = {
    "BOOTED - starting material sequence".postln;

    SynthDef(\materialHitOnce, {
        var which, amp, excite, mat, out, env;

        which = \which.kr(0);   // 0..7
        amp   = \amp.kr(0.25);

        env = EnvGen.ar(Env.perc(0.001, 0.10), doneAction: 2);

        // Excitation: short tone + noise burst
        excite = ((SinOsc.ar(180) * 0.35) + (WhiteNoise.ar(0.65))) * env;

        mat = Select.ar(which, [
            // 0 METAL
            DynKlank.ar(`[ [800, 1200, 2000, 3200], nil, [2.5, 2.0, 1.6, 1.2] ], excite) * 0.8,

            // 1 WOOD
            DynKlank.ar(`[ [180, 260, 420, 650], nil, [1.2, 0.9, 0.7, 0.5] ], excite) * 1.2,

            // 2 GLASS/CERAMIC
            DynKlank.ar(`[ [1500, 2400, 3800, 5200], nil, [2.0, 1.8, 1.5, 1.2] ], excite) * 0.7,

            // 3 BRUSH/AIR
            (CombC.ar(WhiteNoise.ar(0.2) * excite, 0.2, 0.03, 1.2) * 0.9),

            // 4 HOLLOW
            (BPF.ar(excite, 500, 0.2) + BPF.ar(excite, 900, 0.15) + BPF.ar(excite, 1400, 0.12)) * 0.9,

            // 5 SOFT/RUBBER
            FreeVerb.ar(LPF.ar(excite, 900) * 0.9, mix: 0.35, room: 0.25, damp: 0.85),

            // 6 STRINGY
            CombL.ar(excite, 0.15, 0.024, 2.0) * 0.7,

            // 7 SPARKLE
            (Ringz.ar(excite, 2400, 0.7) * 0.7) + (Ringz.ar(excite, 3200, 0.35) * 0.25)
        ]);

        out = Limiter.ar(mat * amp, 0.9);
        Out.ar(0, out ! 2);
    }).add;

    // CRITICAL: wait until the server has the SynthDef
    s.sync;

    // Sequence settings
    ~stepSeconds = 1.2;   // time between hits
    ~loopForever = true;  // set false to play once and stop

    // If an old routine exists from a previous run, stop it
    if(~seqRoutine.notNil) { ~seqRoutine.stop; };

    ~seqRoutine = Routine({
        var i = 0;
        loop {
            ("PLAY material " ++ i).postln;
            Synth(\materialHitOnce, [\which, i, \amp, 0.25]);

            ~stepSeconds.wait;

            i = (i + 1) % 8;

            if((~loopForever.not) && (i == 0)) {
                "DONE (played all 8 once)".postln;
                ^nil;
            };
        }
    }).play(SystemClock);

    "RUNNING: plays 0..7 sequentially. Ctrl+C to stop.".postln;
};

// Headless-safe boot logic (avoids 'already booting' races)
if(s.serverRunning) {
    ~run.value;
} {
    s.waitForBoot { ~run.value; };
    s.boot;
};
