private final static int _parseIndex(String str) {
    final int len = str.length();
    // [Issue#133]: beware of super long indexes; assume we never
    // have arrays over 2 billion entries so ints are fine.
    if (len == 0 || len > 10) {
        return -1;
    }
    for (int i = 0; i < len; ++i) {
        char c = str.charAt(i);
        if (c > '9' || c < '0') {
            return -1;
        }
    }
    if (len == 10) {
        long l = NumberInput.parseLong(str);
        if (l > Integer.MAX_VALUE) {
            return -1;
        }
    }
    return NumberInput.parseInt(str);
}
