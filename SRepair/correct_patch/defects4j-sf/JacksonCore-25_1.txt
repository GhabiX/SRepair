private String _handleOddName2(int startPtr, int hash, int[] codes) throws IOException
{
    _textBuffer.resetWithShared(_inputBuffer, startPtr, (_inputPtr - startPtr));
    char[] outBuf = _textBuffer.getCurrentSegment();
    int outPtr = _textBuffer.getCurrentSegmentSize();
    final int maxCode = codes.length;

    while (true) {
        if (_inputPtr >= _inputEnd) {
            if (!_loadMore()) { // acceptable for now (will error out later)
                break;
            }
        }
        char c = _inputBuffer[_inputPtr];
        int i = (int) c;
        if (i < maxCode) {
            if (codes[i] != 0) {
                break;
            }
        } else if (!Character.isJavaIdentifierPart(c)) {
            break;
        }
        ++_inputPtr;
        hash = (hash * CharsToNameCanonicalizer.HASH_MULT) + i;
        // Ok, let's add char to output:
        outBuf[outPtr++] = c;

        // Need more room?
        if (outPtr >= outBuf.length) {
            outBuf = _textBuffer.finishCurrentSegment();
            outPtr = 0;
        }
    }
    _textBuffer.setCurrentLength(outPtr);
    {
        TextBuffer tb = _textBuffer;
        char[] buf = tb.getTextBuffer();
        int start = tb.getTextOffset();
        int len = tb.size();

        return _symbols.findSymbol(buf, start, len, hash);
    }
}
