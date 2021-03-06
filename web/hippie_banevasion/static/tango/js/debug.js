function BYONDDebug() {
    this.Log = function(message) {}

    this.logWindow = window.open();
    if (this.logWindow == null) {
        return
    }

    this.logWindow.document.write('<html><head><title>Child Log Window</title></head>\x3Cscript>window.opener.console = console;\x3C/script><body><h1>Child Log Window</h1></body></html>');

    this.Log = function(message) {
        if (typeof message == 'object') {
            this.logWindow.document.write((JSON && JSON.stringify ? JSON.stringify(message) : message) + '<br />');
        } else {
            this.logWindow.document.write(message + '<br />');
        }
    }

    this.Log('BYOND IE Bridge loaded');
}

debug = new BYONDDebug();

window.onerror = function(message, url, lineNumber) {
    debug.Log('Error: ' + message + ' url: ' + url + ' line: ' + lineNumber);
    return true;
};

window.onunload = function() {
    if (debug.logWindow && !debug.logWindow.closed) {
        debug.logWindow.close();
    }
};