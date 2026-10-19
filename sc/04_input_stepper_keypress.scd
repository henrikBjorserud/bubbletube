// 04_input_stepper_keypress.scd
// Key controls (in the terminal running sclang):
// n = next input, p = previous input, q = quit

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "BOOT OK - keypress stepper (n=next, p=prev, q=quit)".postln;

    SynthDef(\stepIn, {
        var idx, sig, amp;

        idx = \idx.kr(0);
        amp = \amp.kr(0.12);

        sig = SoundIn.ar(idx);
        sig = HPF.ar(sig, 80);
        sig = LPF.ar(sig, 8000);
        sig = Compander.ar(sig, sig, 0.25, 1, 0.2, 0.003, 0.15);

        Out.ar(0, (sig * amp) ! 2);
    }).add;

    s.sync; // wait until SynthDef is received by server

    ~maxCh = 15;
    ~idx = 0;
    x = Synth(\stepIn, [\idx, ~idx, \amp, 0.12]);
    ("NOW MONITORING INPUT: " ++ ~idx).postln;

    // Read single chars from stdin (requires sclang to have a TTY)
    stdin = File("/dev/stdin", "r");

    r = Routine({
        var c;
        loop {
            c = stdin.getChar;

            if(c.notNil) {
                if(c == $n) {
                    ~idx = (~idx + 1) % (~maxCh + 1);
                    x.set(\idx, ~idx);
                    ("NOW MONITORING INPUT: " ++ ~idx).postln;
                };

                if(c == $p) {
                    ~idx = (~idx - 1);
                    if(~idx < 0) { ~idx = ~maxCh };
                    x.set(\idx, ~idx);
                    ("NOW MONITORING INPUT: " ++ ~idx).postln;
                };

                if(c == $q) {
                    "Quitting...".postln;
                    x.free;
                    s.quit;
                    stdin.close;
                    ^nil;
                };
            };

            0.02.wait;
        }
    }).play(SystemClock);
};

s.boot;
