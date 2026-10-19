// diag_channels.scd — hit piezos to see which input channels have signal
// Run: sclang /Users/tactile/sc/diag_channels.scd

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "Monitoring all 20 input channels — hit piezos now".postln;

    {
        var amps = Array.fill(20, { |i| Amplitude.kr(SoundIn.ar(i), 0.05, 0.2) });
        SendReply.kr(Impulse.kr(4), '/amps', amps);
    }.play;

    OSCFunc({ |msg|
        var vals = msg[3..];
        var hits = "";
        20.do { |i|
            if (vals[i] > 0.005) { hits = hits ++ "ch" ++ i ++ "=" ++ vals[i].round(0.001) ++ " " }
        };
        if (hits.size > 0) { hits.postln };
    }, '/amps');
};
