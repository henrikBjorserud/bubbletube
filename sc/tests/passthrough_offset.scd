// Test each offset separately — 8 seconds each, prints which is active
Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {

    #[0, 2, 4, 6, 8, 10, 12].do { |offset|
        var msg = "=== OFFSET % ===".format(offset);
        msg.postln;
        { Mix(Array.fill(8, { |i| SoundIn.ar((i + offset).min(19)) })) * 0.3 ! 2 }.play;
        8.wait;
        s.freeAll;
        0.1.wait;
    };

    "DONE".postln;
};

s.boot;
