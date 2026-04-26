function x = parse_numeric_column(raw)
%PARSE_NUMERIC_COLUMN Robust conversion of heterogeneous table column to double.

if isnumeric(raw)
    x = double(raw);
    return;
end

if islogical(raw)
    x = double(raw);
    return;
end

if isdatetime(raw) || isduration(raw)
    x = double(raw);
    return;
end

if isstring(raw) || ischar(raw) || iscellstr(raw) || iscell(raw)
    s = string(raw);
    s = strtrim(s);
    s(s == "") = missing;
    x = str2double(s);
    return;
end

error("Unsupported column type for numeric parsing: %s", class(raw));

end

