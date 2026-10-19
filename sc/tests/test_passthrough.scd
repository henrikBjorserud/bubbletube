// test_passthrough.scd — raw ADAT -> output, high gain
// First plays a 1-second 440Hz beep so you know output works, then passes ADAT through.

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "Playing test beep first...".postln;
    { SinOsc.ar(440, 0, 0.3) ! 2 }.play;

    AppClock.sched(1.5, {
        s.freeAll;
        "PASSTHROUGH: hit piezos hard".postln;
        { Limiter.ar(Mix(SoundIn.ar(Array.series(8, 12))) * 50.0 ! 2, 0.9) }.play;
        nil
    });
};
