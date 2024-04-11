public void setSelected(Option option) throws AlreadySelectedException
{
    if (option == null)
    {
        // reset the option previously selected
        selected = null;
        return;
    }
    
    // if no option has already been selected or the 
    // same option is being reselected then set the
    // selected member variable
    if (selected == null || selected.equals(option.getKey()))
    {
        selected = option.getKey();
    }
    else
    {
        throw new AlreadySelectedException(this, option);
    }
}
