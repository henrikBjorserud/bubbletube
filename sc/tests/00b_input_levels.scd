// 00b_input_levels.scd
// Prints amplitude for all 20 inputs every second.
// Touch each piezo and watch which channel number reacts.

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "BOOT OK - watching all 20 inputs".postln;
    "Touch a piezo and watch which channel number shows a value > 0.".postln;

    SynthDef(\levelWatch, {
        var amps = Array.fill(20, { |i|
            Amplitude.kr(SoundIn.ar(i), 0.002, 0.1)
        });
        SendReply.kr(Impulse.kr(2), '/levels', amps);
    }).add;

    s.sync;

    OSCdef(\levels, { |msg|
        var amps = msg[3..];
        amps.do { |a, i|
            if(i >= 8) { // only show ADAT channels 8..15
                ("input " ++ i ++ ": " ++ a.round(0.0001)).postln;
            };
        };
        "---".postln;
    }, '/levels');

    Synth(\levelWatch);

    "RUNNING: reporting every 0.5s. Ctrl+C to stop.".postln;
};

s.boot;
