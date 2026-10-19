// Mix all 20 input channels to output — tells us if SC hears any piezo at all
Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    { Mix(SoundIn.ar(Array.series(20))) * 0.1 ! 2 }.play;
    "RUNNING — touch wall, all 20 channels mixed".postln;
};
s.boot;
