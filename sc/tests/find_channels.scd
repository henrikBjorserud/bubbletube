// Binary search for ADAT channels — 4s per pair
Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    // Test channels in pairs — touch wall for each, listen for sound
    #[0,2,4,6,8,10,12,14,16,18].do { |ch|
        "=== CHANNELS % and % ===".format(ch, ch+1).postln;
        { (SoundIn.ar(ch) + SoundIn.ar(ch+1)) * 2.0 ! 2 }.play;
        4.wait;
        s.freeAll;
        0.1.wait;
    };
    "DONE".postln;
};

s.boot;
