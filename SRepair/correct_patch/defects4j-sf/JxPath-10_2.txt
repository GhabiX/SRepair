public final Object computeValue(EvalContext context) {
    return compute(args[0].compute(context), args[1].compute(context)) 
            ? Boolean.TRUE : Boolean.FALSE;
}