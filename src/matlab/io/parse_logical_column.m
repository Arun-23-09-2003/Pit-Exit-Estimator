function y = parse_logical_column(raw)
%PARSE_LOGICAL_COLUMN Robust conversion of table column to logical.

if islogical(raw)
    y = raw;
    return;
end

if isnumeric(raw)
    y = raw ~= 0;
    return;
end

s = lower(strtrim(string(raw)));
y = false(size(s));

true_tokens = ["true", "1", "t", "yes", "y"];
false_tokens = ["false", "0", "f", "no", "n", ""];

for i = 1:numel(s)
    token = s(i);
    if any(token == true_tokens)
        y(i) = true;
    elseif any(token == false_tokens) || ismissing(token)
        y(i) = false;
    else
        num_val = str2double(token);
        if ~isnan(num_val)
            y(i) = num_val ~= 0;
        else
            y(i) = false;
        end
    end
end

end

