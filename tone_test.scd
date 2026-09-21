Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numOutputBusChannels = 8;
s.waitForBoot {
    { SinOsc.ar(440, 0, 0.3) ! 2 }.play;
    "TONE PLAYING on outputs 1-2".postln;
};
s.boot;
