####################################################
#    SOME GLOBAL VARIABLES    #
####################################################


_REGEX_B = r"benefit_(.*\D)_yr(.*\d)$"
_REGEX_C = r"cost_(.*\D)_yr(.*\d)$"
_REGEX_E = r"emission_(.*\D)_yr(.*\d)$"
_REGEX_L = r"group_(.*\d)_L_(.*\D)"
_REGEX_X = r"group_(.*\d)_X_(.*\D)"



####################################################
#    SETUP FUNCTIONS FOR LOADING/MODIFYING DATA    #
####################################################

"""Build fields for aggregate measures
"""
function build_dict_fields_aggregate(
    dict_years_to_total::Dict,
    field_prefix::String,
)::Tuple{Dict{Any, String}, Dict{String, Any}}

    dict_out = Dict()
    dict_out_rev = Dict()
    
    for k in keys(dict_years_to_total)
        out = "$(field_prefix)_$(k)"
        dict_out[k] = out
        dict_out_rev[out] = k
    end

    out = (dict_out, dict_out_rev)

    return out
end



"""Build the training data to use for the NN metamodel.

- `dataset`::Parquet2.Dataset
    Parquet dataset use to get column names
- `df`::DataFrame
    DataFrame storing training data, derived from dataset
- `alpha_outliers`::Union{Float64, Int64, Nothing}
    Optional specification of a scalar used to identify outliers; Find outliers are those 
    values that lie beyond the threshold of μ +/- α*σ, where
        * α:    is a positive parameter set by the user;
        * μ:    is the mean (est); and
        * σ:    is the standard deviation (est) from the 
                column.
    If `nothing`, does not filter.
"""
function build_training_data(
    dataset::Parquet2.Dataset,
    df::DataFrame;
    alpha_outliers::Union{Float64, Int64, Nothing} = nothing,
)
    ##  GET DICTIONARIES

    # fields for grouping
    dict_b_field_to_grp, dict_b_grp_to_field = get_dicts_fields_from_regex2(names(dataset), _REGEX_B, )
    dict_c_field_to_grp, dict_c_grp_to_field = get_dicts_fields_from_regex2(names(dataset), _REGEX_C, )
    dict_e_field_to_grp, dict_e_grp_to_field = get_dicts_fields_from_regex2(names(dataset), _REGEX_E, )
    dict_l_field_to_grp, dict_l_grp_to_field = get_dicts_fields_from_regex(names(dataset), _REGEX_L, )
    dict_x_field_to_grp, dict_x_grp_to_field = get_dicts_fields_from_regex(names(dataset), _REGEX_X, )
    
    # benefits
    dict_benefit_years_to_total = get_dict_aggregates_by_year_from_regex(
        df_training,
        dataset,
        _REGEX_B;
        aggregate_by_group = false,
    )
    
    # costs by sector (multiply by negative one to make costs)
    dict_cost_years_to_total = get_dict_aggregates_by_year_from_regex(
        df_training,
        dataset,
        _REGEX_C;
        aggregate_by_group = false,
        factor = -1.0,
    )

    # get benefit and cost fields and year maps
    dict_b_yr_to_field_agg, dict_b_field_agg_to_yr = build_dict_fields_aggregate(dict_benefit_years_to_total, "benefits", )
    dict_c_yr_to_field_agg, dict_c_field_agg_to_yr  = build_dict_fields_aggregate(dict_benefit_years_to_total, "costs", )

    
    # turn into fields as well
    fields_b = get_fields_from_dict(dict_b_field_agg_to_yr, )
    fields_c = get_fields_from_dict(dict_c_field_agg_to_yr, )
    fields_e = get_fields_from_dict(dict_e_field_to_grp, )
    fields_l = get_fields_from_dict(dict_l_field_to_grp, )
    fields_x = get_fields_from_dict(dict_x_field_to_grp, )

    
    ##  INITIALIZE DATAFRAME WITH BENEFITS AND COSTS

    df_out = DataFrame()

    # benefits
    for (k, v) in dict_b_field_agg_to_yr
        df_out[:, k] = get(dict_benefit_years_to_total, v, nothing)
    end
    
    # costs
    for (k, v) in dict_c_field_agg_to_yr
        df_out[:, k] = get(dict_cost_years_to_total, v, nothing)
    end

    # emissions, levers, exogenous uncertainties--pull directly from dataset
    for fld in [fields_e; fields_l; fields_x]
        df_out[!, fld] = copy(df_training[!, fld])
    end

    # drop any rows with missing data
    dropmissing!(df_out)

    
    ##  GET OUTPUTS
        
    # fields
    fields_X = [fields_l; fields_x]
    fields_Y = [fields_b; fields_c; fields_e]

    # get X and Y
    df_X, fields_X = drop_invalid_inputs(
        select(df_out, fields_X, )
    )
    df_Y, fields_Y = drop_invalid_inputs(
        select(df_out, fields_Y, )
    )

    X = Matrix(df_X, )
    Y = Matrix(df_Y, )

    # finally, filter any outliers
    X, Y = filter_outliers(X, Y, alpha_outliers);

    
    out = (
        fields_X,
        fields_Y,
        X,
        Y,
    )
    
    return out
end


"""Find outliers that lie beyond the threshold of μ +/- α*σ, where
    μ is the mean (est) and σ is the standard deviation (est) from the 
    column. α is a positive parameter set by the user. Returns a binary 
    vector giving the position of outliers.
""" 
function filter_outliers(
    X::Matrix,
    Y::Matrix,
    α::Union{Float64, Int64, Nothing},
)
     
    ##  FILTER OUTLIERS?
    
    if !isa(α, Nothing)
        # map to each column, then drop rows associated with an outlier
        mat_flags_outliers = hcat(flag_outlier.(eachcol(Y), α)...);
        rows_drop = maximum.(eachrow(mat_flags_outliers)) .== 0;
        rows_keep = Bool.(rows_drop)

        # filter
        X = X[rows_keep, :]
        Y = Y[rows_keep,:]
    end

    out = (X, Y)
    
    return out
end



"""Remove any columns with no information; drops those with 0 variance (1 value)
"""
function drop_invalid_inputs(
    df::DataFrame,
)::Tuple{DataFrame, Vector{String}}

    # set extraction fields
    fields = filter(
        x -> (
            length(unique(df[:, x])) > 1
        ),
        names(df)
    )

    df_out = select(df, fields, )
    
    out = (df_out, fields)

    return out
end



"""Find outliers that lie beyond the threshold of μ +/- α*σ, where
    μ is the mean (est) and σ is the standard deviation (est) from the 
    column. α is a positive parameter set by the user. Returns a binary 
    vector giving the position of outliers.
"""
function flag_outlier(
    vec::AbstractArray,
    α::Float64,
)
    # get mean and standard deviation
    μ = mean(vec)
    σ = std(vec)

    avec = abs.(vec .- μ)
    inds = findall(x -> (x > α*σ), avec)
    out = zeros(size(vec))

    out[inds] .= 1

    return out
end



"""Get a dictionary that maps a year to a total value vector from the dataframe.

```
get_dict_aggregates_by_year_from_regex(
    df::DataFrame,
    dataset::Parquet2.Dataset,
    regex::Regex;
    aggregate_by_group::Bool = false,
    factor::Float64 = 1.0,
)::Dict{Int64, Vector{Float64}}
```



factor : Float64 
    Optional factor that can be multipled by vectors
"""
function get_dict_aggregates_by_year_from_regex(
    df::DataFrame,
    dataset::Parquet2.Dataset,
    regex::Regex;
    aggregate_by_group::Bool = false,
    factor::Float64 = 1.0,
)::Dict{Any, Vector{Float64}}
    # get fields
    dict_fields_to_grp, dict_grps_to_field = get_dicts_fields_from_regex2(
        names(dataset),
        regex, 
    )

    # initialize output dictionary
    dict_out = Dict()

    for item in dict_grps_to_field
        key, value = item
        _, yr = key

        # get key and see if the vector exists
        key_check = aggregate_by_group ? key : yr
        vec = get(dict_out, key_check, nothing)

        # 
        if isa(vec, Nothing)
            dict_out[key_check] = Vector{Float64}(copy(df[:, value]))*factor
            continue
        end

        dict_out[key_check] += Vector{Float64}(df[:, value])*factor
        
    end

    return dict_out
end



"""Get fields that match a regex with 1 capture (levers vs. exogenous 
    uncertainties)
"""
function get_dicts_fields_from_regex(
    vec_names::Vector{String},
    regex::Regex,
)
    out = [match(regex, x) for x in vec_names]
    dict_fld_to_grp = Dict{}()
    dict_grp_to_fld = Dict{}()

    for elem in out
        isa(elem, Nothing) && continue

        # try to extract group, add to dictionary
        grp = tryparse(Int64, elem.captures[1], )
        match_str = string(elem.match, )
        
        dict_fld_to_grp[match_str] = grp
        dict_grp_to_fld[grp] = match_str
        
    end

    out = (
        dict_fld_to_grp, 
        dict_grp_to_fld, 
    )

    return out
end



"""Get fields that match a regex with 2 captures (benefits, costs, emissions)
"""
function get_dicts_fields_from_regex2(
    vec_names::Vector{String},
    regex::Regex,
)
    out = [match(regex, x) for x in vec_names]
    dict_fld_to_grp = Dict{}()
    dict_grp_to_fld = Dict{}()

    for elem in out
        isa(elem, Nothing) && continue

        # try to extract group, add to dictionary
        grp = string( elem.captures[1])
        yr = tryparse(Int64, elem.captures[2], )
        match_str = string(elem.match, )
        tup = (grp, yr)
        
        dict_fld_to_grp[match_str] = tup
        dict_grp_to_fld[tup] = match_str
        
    end

    out = (
        dict_fld_to_grp, 
        dict_grp_to_fld, 
    )

    return out
end



"""Get fields (ordered) from a dictionary
"""
function get_fields_from_dict(
    dict_fields_to_grp::Dict,
)
    # define a sorting function
    sorter(x::String) = get(dict_fields_to_grp, x, nothing)
    
    fields_out = sort(collect(keys(dict_fields_to_grp)), by = sorter)

    return fields_out
end
    