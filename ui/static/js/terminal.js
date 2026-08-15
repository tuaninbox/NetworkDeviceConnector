let ws = null;
let term = null;
let fitAddon = null;
 

// function startInteractive() {
//     const deviceId = getSelectedDevice();
//     if (!deviceId) {
//         showMessage("Select a device first");
//         return;
//     }

//     document.getElementById("run-output-container").classList.add("hidden");
//     document.getElementById("terminal-container").classList.remove("hidden");
//     // document.getElementById("command-header").classList.remove("sticky", "top-0");
//     // document.getElementById("terminal-container").offsetHeight; 

//     // Close previous WS
//     if (ws) ws.close();

//     // Create WebSocket FIRST
//     ws = new WebSocket(`ws://${window.location.host}/connector/ws/${deviceId}`);

//     // THEN init terminal
//     ws.onopen = () => {
//         initTerminal();   // <-- moved here
//         term.write(`\r\n[Interactive session started for ${deviceId}]\r\n`);
//         sendResize();
//     };

//     ws.onclose = () => {
//         term.write(`\r\n[Interactive session closed]\r\n`);
//         ws = null;
//     };
// }

function startInteractive() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        showMessage("Select a device first");
        return;
    }

    window.open(`/ui/interactive?device=${deviceId}`, "_blank");
}


  //initTerminal
function initTerminal() {
    // Always recreate terminal for fresh session
    if (term) {
        term.dispose();
        term = null;
    }

    fitAddon = new FitAddon.FitAddon();
    term = new Terminal({
        cursorBlink: true,
        convertEol: true,
        fontSize: 14,
        theme: {
            background: "#000000",
            foreground: "#00ff00"
        }
    });

    term.loadAddon(fitAddon);

    const container = document.getElementById("terminal-container");
    term.open(container);
    fitAddon.fit();

    // // Send keystrokes to backend
    // term.onData(data => {
    //     if (ws) ws.send(data);
    // });
    let buffer = "";        // full command text
    let cursor = 0;         // cursor position inside buffer
    let prompt = "# ";      // fallback prompt until backend sends real one

    // Backend messages update prompt + output
    if (ws) {
        ws.onmessage = event => {
            const msg = JSON.parse(event.data);

            if (msg.output) {
                term.write("\r\n" + msg.output + "\r\n");
            }

            if (msg.prompt) {
                prompt = msg.prompt;
            }

            redrawLine();
        };
    }

    term.onData(data => {
        // ENTER
        if (data === "\r") {
            term.write("\r\n");
            ws.send(buffer);
            buffer = "";
            cursor = 0;
            return;
        }

        // BACKSPACE
        if (data === "\x7f") {
            if (cursor > 0) {
                buffer = buffer.slice(0, cursor - 1) + buffer.slice(cursor);
                cursor--;
                redrawLine();
            }
            return;
        }

        // LEFT ARROW
        if (data === "\x1b[D") {
            if (cursor > 0) {
                cursor--;
                term.write("\x1b[D");
            }
            return;
        }

        // RIGHT ARROW
        if (data === "\x1b[C") {
            if (cursor < buffer.length) {
                cursor++;
                term.write("\x1b[C");
            }
            return;
        }

        // Printable characters
        if (data >= " " && data <= "~") {
            buffer = buffer.slice(0, cursor) + data + buffer.slice(cursor);
            cursor++;
            redrawLine();
            return;
        }
    });

    // Helper to redraw the current line WITH PROMPT
    function redrawLine() {
        term.write("\x1b[2K\r");          // clear line
        term.write(prompt + buffer);

        const moveLeft = buffer.length - cursor;
        if (moveLeft > 0) {
            term.write(`\x1b[${moveLeft}D`);
        }
    }
}


// ---------------------------
// Terminal Resize → Backend
// ---------------------------
function sendResize() {
    if (!ws || !term) return;
    const cols = term.cols;
    const rows = term.rows;
    ws.send(`__resize__:${cols}:${rows}`);
}
