public void describeTo(Description description) {
    description.appendText("same(");
    appendQuoting(description);
    description.appendText(wanted == null ? "null" : wanted.toString());
    appendQuoting(description);
    description.appendText(")");
}
