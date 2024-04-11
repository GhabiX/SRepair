protected Object readResolve() {
    calculateHashCode(keys);
    return this;
}