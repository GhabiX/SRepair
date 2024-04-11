public void acceptJsonFormatVisitor(JsonFormatVisitorWrapper visitor, JavaType typeHint) throws JsonMappingException
{
    if (_isInt) {
        visitIntFormat(visitor, typeHint, JsonParser.NumberType.BIG_INTEGER);
    } else {
        Class<?> h = handledType();
        if (h == BigDecimal.class) {
            visitFloatFormat(visitor, typeHint, JsonParser.NumberType.BIG_DECIMAL);
        } else {
            // otherwise bit unclear what to call... but let's try:
            /*JsonNumberFormatVisitor v2 =*/ visitor.expectNumberFormat(typeHint);
        }
    }
}
