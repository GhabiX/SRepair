public String nextTextValue() throws IOException
{
    _binaryValue = null;
    if (_nextToken != null) {
        JsonToken t = _nextToken;
        _currToken = t;
        _nextToken = null;

        // expected case; yes, got a String
        if (t == JsonToken.VALUE_STRING) {
            return _currText;
        }
        _updateState(t);
        return null;
    }

    int token = _xmlTokens.next();

    // mostly copied from 'nextToken()'
    while (token == XmlTokenStream.XML_START_ELEMENT) {
        if (_mayBeLeaf) {
            _nextToken = JsonToken.FIELD_NAME;
            _parsingContext = _parsingContext.createChildObjectContext(-1, -1);
            _currToken = JsonToken.START_OBJECT;
            return null;
        }
        if (_parsingContext.inArray()) {
            token = _xmlTokens.next();
            _mayBeLeaf = true;
            continue;
        }
        String name = _xmlTokens.getLocalName();
        _parsingContext.setCurrentName(name);
        if (_namesToWrap != null && _namesToWrap.contains(name)) {
            _xmlTokens.repeatStartElement();
        }
        _mayBeLeaf = true;
        _currToken = JsonToken.FIELD_NAME;
        return null;
    }

    // Ok; beyond start element, what do we get?
    switch (token) {
    case XmlTokenStream.XML_END_ELEMENT:
        if (_mayBeLeaf) {
            // NOTE: this is different from nextToken() -- produce "", NOT null
            _mayBeLeaf = false;
            _currToken = JsonToken.VALUE_STRING;
            return (_currText = "");
        }
        _currToken = _parsingContext.inArray() ? JsonToken.END_ARRAY : JsonToken.END_OBJECT;
        _parsingContext = _parsingContext.getParent();
        _namesToWrap = _parsingContext.getNamesToWrap();
        break;
    case XmlTokenStream.XML_ATTRIBUTE_NAME:
        // If there was a chance of leaf node, no more...
        if (_mayBeLeaf) {
            _mayBeLeaf = false;
            _nextToken = JsonToken.FIELD_NAME;
            _currText = _xmlTokens.getText();
            _parsingContext = _parsingContext.createChildObjectContext(-1, -1);
            _currToken = JsonToken.START_OBJECT;
        } else {
            _parsingContext.setCurrentName(_xmlTokens.getLocalName());
            _currToken = JsonToken.FIELD_NAME;
        }
        break;
    case XmlTokenStream.XML_ATTRIBUTE_VALUE:
        _currText = _xmlTokens.getText();
        _currToken = JsonToken.VALUE_STRING;
        return _currText;
    case XmlTokenStream.XML_TEXT:
        _currText = _xmlTokens.getText();
        if (_mayBeLeaf) {
            _mayBeLeaf = false;
            // Also: must skip following END_ELEMENT
            _xmlTokens.skipEndElement();

            // NOTE: this is different from nextToken() -- NO work-around
            // for otherwise empty List/array
            _currToken = JsonToken.VALUE_STRING;
            return _currText;
        }
        // If not a leaf, need to transform into property...
        _parsingContext.setCurrentName(_cfgNameForTextElement);
        _nextToken = JsonToken.VALUE_STRING;
        _currToken = JsonToken.FIELD_NAME;
        break;
    case XmlTokenStream.XML_END:
        _currToken = null;
    }
    return null;
}