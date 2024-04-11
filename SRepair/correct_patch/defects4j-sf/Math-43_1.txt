public void addValue(double value) {
    sumImpl.increment(value);
    sumsqImpl.increment(value);
    minImpl.increment(value);
    maxImpl.increment(value);
    sumLogImpl.increment(value);
    secondMoment.increment(value);
    // If mean, variance or geomean have been overridden,
    // need to increment these
    if (meanImpl != mean) {
        meanImpl.increment(value);
    }
    if (varianceImpl != variance) {
        varianceImpl.increment(value);
    }
    if (geoMeanImpl != geoMean) {
        geoMeanImpl.increment(value);
    }
    n++;
}
