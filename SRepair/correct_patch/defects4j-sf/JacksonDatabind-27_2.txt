protected Object deserializeUsingPropertyBasedWithExternalTypeId(JsonParser p, DeserializationContext ctxt)
    throws IOException
{
    final ExternalTypeHandler ext = _externalTypeIdHandler.start();
    final PropertyBasedCreator creator = _propertyBasedCreator;
    PropertyValueBuffer buffer = creator.startBuilding(p, ctxt, _objectIdReader);

    TokenBuffer tokens = new TokenBuffer(p);
    tokens.writeStartObject();

    JsonToken t = p.getCurrentToken();
    for (; t == JsonToken.FIELD_NAME; t = p.nextToken()) {
        String propName = p.getCurrentName();
        p.nextToken(); // to point to value
        // creator property?
        SettableBeanProperty creatorProp = creator.findCreatorProperty(propName);
        if (creatorProp != null) {
            // first: let's check to see if this might be part of value with external type id:
            // 11-Sep-2015, tatu: Important; do NOT pass buffer as last arg, but null,
            //   since it is not the bean
            if (ext.handlePropertyValue(p, ctxt, propName, null)) {
                ;
            } else {
                // Last creator property to set?
                if (buffer.assignParameter(creatorProp, _deserializeWithErrorWrapping(p, ctxt, creatorProp))) {
                    t = p.nextToken(); // to move to following FIELD_NAME/END_OBJECT
                    Object bean;
                    try {
                        bean = creator.build(ctxt, buffer);
                    } catch (Exception e) {
                        wrapAndThrow(e, _beanType.getRawClass(), propName, ctxt);
                        continue; // never gets here
                    }
                    // if so, need to copy all remaining tokens into buffer
                    while (t == JsonToken.FIELD_NAME) {
                        p.nextToken(); // to skip name
                        tokens.copyCurrentStructure(p);
                        t = p.nextToken();
                    }
                    if (bean.getClass() != _beanType.getRawClass()) {
                        // !!! 08-Jul-2011, tatu: Could theoretically support; but for now
                        //   it's too complicated, so bail out
                        throw ctxt.mappingException("Can not create polymorphic instances with unwrapped values");
                    }
                    return ext.complete(p, ctxt, bean);
                }
            }
            continue;
        }
        // Object Id property?
        if (buffer.readIdProperty(propName)) {
            continue;
        }
        // regular property? needs buffering
        SettableBeanProperty prop = _beanProperties.find(propName);
        if (prop != null) {
            buffer.bufferProperty(prop, prop.deserialize(p, ctxt));
            continue;
        }
        // external type id (or property that depends on it)?
        if (ext.handlePropertyValue(p, ctxt, propName, null)) {
            continue;
        }
        /* As per [JACKSON-313], things marked as ignorable should not be
         * passed to any setter
         */
        if (_ignorableProps != null && _ignorableProps.contains(propName)) {
            handleIgnoredProperty(p, ctxt, handledType(), propName);
            continue;
        }
        // "any property"?
        if (_anySetter != null) {
            buffer.bufferAnyProperty(_anySetter, propName, _anySetter.deserialize(p, ctxt));
        }
    }

    // We hit END_OBJECT; resolve the pieces:
    try {
        return ext.complete(p, ctxt, buffer, creator);
    } catch (Exception e) {
        wrapInstantiationProblem(e, ctxt);
        return null; // never gets here
    }
}
