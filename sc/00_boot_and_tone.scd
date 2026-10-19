// 00_boot_and_tone.scd
Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "Server booted".postln;

    x = { Out.ar(0, SinOsc.ar(220) * 0.1 * EnvGen.kr(Env.asr(1, 1, 2)) ! 2) }.play;

    "Playing tone for 10 seconds...".postln;
    SystemClock.sched(10, {
        x.release(2);
        "Stopping...".postln;
        nil
    });
};

s.boot;

