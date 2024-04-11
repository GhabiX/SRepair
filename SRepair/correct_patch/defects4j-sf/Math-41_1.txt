public double evaluate(final double[] values, final double[] weights,
                       final double mean, final int begin, final int length) {

    double var = Double.NaN;

    if (test(values, weights, begin, length)) {
        if (length == 1) {
            var = 0.0;
        } else if (length > 1) {
            double accum = 0.0;
            double dev = 0.0;
            double accum2 = 0.0;
            for (int i = begin; i < begin + length; i++) {
                dev = values[i] - mean;
                accum += weights[i] * (dev * dev);
                accum2 += weights[i] * dev;
            }

            double sumWts = 0;
            for (int i = begin; i < begin + length; i++) {
                sumWts += weights[i];
            }

            if (isBiasCorrected) {
                var = (accum - (accum2 * accum2 / sumWts)) / (sumWts - 1.0);
            } else {
                var = (accum - (accum2 * accum2 / sumWts)) / sumWts;
            }
        }
    }
    return var;
}
