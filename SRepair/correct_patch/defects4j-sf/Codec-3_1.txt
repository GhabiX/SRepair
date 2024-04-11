private int handleG(String value, 
                    DoubleMetaphoneResult result, 
                    int index, 
                    boolean slavoGermanic) {
    if (charAt(value, index + 1) == 'H') {
        index = handleGH(value, result, index);
    } else if (charAt(value, index + 1) == 'N') {
        if (index == 1 && isVowel(charAt(value, 0)) && !slavoGermanic) {
            result.append("KN", "N");
        } else if (!contains(value, index + 2, 2, "EY") && 
                   charAt(value, index + 1) != 'Y' && !slavoGermanic) {
            result.append("N", "KN");
        } else {
            result.append("KN");
        }
        index = index + 2;
    } else if (contains(value, index + 1, 2, "LI") && !slavoGermanic) {
        result.append("KL", "L");
        index += 2;
    } else if (index == 0 && (charAt(value, index + 1) == 'Y' || contains(value, index + 1, 2, ES_EP_EB_EL_EY_IB_IL_IN_IE_EI_ER))) {
        //-- -ges-, -gep-, -gel-, -gie- at beginning --//
        result.append('K', 'J');
        index += 2;
    } else if ((contains(value, index + 1, 2, "ER") || 
                charAt(value, index + 1) == 'Y') &&
               !contains(value, 0, 6, "DANGER", "RANGER", "MANGER") &&
               !contains(value, index - 1, 1, "E", "I") && 
               !contains(value, index - 1, 3, "RGY", "OGY")) {
        //-- -ger-, -gy- --//
        result.append('K', 'J');
        index += 2;
    } else if (contains(value, index + 1, 1, "E", "I", "Y") || 
               contains(value, index - 1, 4, "AGGI", "OGGI")) {
        //-- Italian "biaggi" --//
        if ((contains(value, 0 ,4, "VAN ", "VON ") || contains(value, 0, 3, "SCH")) || contains(value, index + 1, 2, "ET")) {
            //-- obvious germanic --//
            result.append('K');
        } else if (contains(value, index + 1, 3, "IER")) {
            result.append('J');
        } else {
            result.append('J', 'K');
        }
        index += 2;
    } else if (charAt(value, index + 1) == 'G') {
        index += 2;
        result.append('K');
    } else {
        index++;
        result.append('K');
    }
    return index;
}
