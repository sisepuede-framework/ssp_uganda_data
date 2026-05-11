"""Code for building the Policy and Measures experiment for Excel tool
"""

import numpy as np
import os, os.path
import pandas as pd
import pathlib
import sisepuede.transformers.strategies as tst
import sisepuede.utilities._toolbox as sf
from typing import *






##########################
#    GLOBAL VARIABLES    #
##########################

_BLANK = "BLANK"

# fields
_FIELD_CW_DESCRIPTION = "description"
_FIELD_CW_SECTOR = "sector"
_FIELD_CW_TRANSFORMATIONS_INF = "transformations_lower"
_FIELD_CW_TRANSFORMATIONS_SUP = "transformations_upper"
_FIELD_PAM_ID = "pam_id"
_FIELD_PAM_NAME = "pam_name"

# prefixes
_PREFIX_CODE_PORTFOLIO = "PFLO"
_PREFIX_EXPERIMENT_INF = "PAM_INF"
_PREFIX_EXPERIMENT_SUP = "PAM_SUP"
_PREFIX_PAM_IN_ID = "PAM_"

# sheets 
_SHEET_NAME_CW = "pam_transformation_crosswalk"




###################
#    FUNCTIONS    #
###################


def build_pam_strategy_code(
    strategy: 'Strategy',
    suffix: str,
    pam_type: str,
) -> str:
    """Build a new strategy code
    """

    pam_type = pam_type.upper().replace(_PREFIX_PAM_IN_ID, "")
    out = str(suffix).upper()
    
    out = f"{strategy.code}_{_PREFIX_PAM_IN_ID}{out}_{pam_type}"

    return out

def get_pam_ids_from_strategy_code(
    strategy_code: str,
    prefix: str = _PREFIX_PAM_IN_ID,
) -> Union[str, None]:
    """Get the PAM ID associated with a run. Returns None if unable to retrieve
        a code.
    """

    # split
    codes = strategy_code.split(prefix, )
    if len(codes) == 1:
        return None
    
    codes = codes[1].split("_")
    ids_out = get_pam_ids_from_suffix(codes[0])
    inf_sup = codes[1]

    out = (
        ids_out,
        inf_sup,
    )

    return out



def get_pam_ids_from_suffix(
    suffix: List[str],
    delim: str = ".",
    prefix: str = _PREFIX_PAM_IN_ID,
) -> str:
    """Using a set of PAM ids, build a suffix to use in a transformation.
    """
    out = [f"{prefix}{x}" for x in suffix.split(delim, )]
    
    return out




def build_pam_strategy_name(
    strategy: 'Strategy',
    suffix: str,
    pam_type: str,
) -> str:
    """Build a new strategy code
    """

    pam_type = pam_type.upper()

    desc = (
        "overwriting from upper strategies"
        if pam_type.upper() == _PREFIX_EXPERIMENT_INF
        else "removing from lower strategies"
    )
    out = f"{strategy.name} with {desc} for PAM {suffix}"

    return out



def build_pam_suffix_for_transformation(
    ids: List[str],
    delim: str = ".",
    prefix: str = _PREFIX_PAM_IN_ID,
) -> str:
    """Using a set of PAM ids, build a suffix to use in a transformation.
    """
    
    out = [x.replace(prefix, "") for x in list(ids)]
    out = delim.join(out, )

    return out



def check_pam_cw_specification(
    df: pd.DataFrame,
) -> None:
    """Ensure that there aren't multiple specifications of a lower to 
        upper map. Raises runtime errors if INF -> SUP or SUP -> INF
        is not a function.
    """

    # reduce
    df_map = (
        df[
            [
                _FIELD_CW_TRANSFORMATIONS_INF, 
                _FIELD_CW_TRANSFORMATIONS_SUP
            ]
        ]
        .drop_duplicates()
    )

    
    ##  CHECK THAT INF -> SUP IS A FUNCTION
    
    dfg = df_map.groupby(
        _FIELD_CW_TRANSFORMATIONS_INF
    )
    
    max_len = 1
    
    for grp, df in dfg:
        if grp[0] == "": continue

        max_len = max(max_len, df.shape[0])
        if max_len > 1:
            msg = f"""A single lower-bound transformation set maps to multiple
            upper-bound transformation sets.

            Diagnostic
            ----------
            lower-bound set:
            {grp[0]}
            """
            raise RuntimeError(msg)


    ##  CHECK THAT SUP -> INF IS A FUNCTION
    
    dfg = df_map.groupby(
        _FIELD_CW_TRANSFORMATIONS_SUP
    )
    
    max_len = 1
    
    for grp, df in dfg:
        if grp[0] == "": continue

        max_len = max(max_len, df.shape[0])
        if max_len > 1:
            msg = f"""A single upper-bound transformation set maps to multiple
            lower-bound transformat
            ion sets.

            Diagnostic
            ----------
            upper-bound set:
            {grp[0]}
            """
            raise RuntimeError(msg)

    return None



def get_pam_crosswalk(
    path: pathlib.Path,
    return_df_only: bool = False, 
    sheet_name: str = _SHEET_NAME_CW,
) -> Union[Dict[str, List[str]], pd.DataFrame]:
    """Get the crosswalk mapping PAM ids to transformations. 
    """

    # try reading the data frame
    try:
        df = pd.read_excel(path, sheet_name = sheet_name, )
    except Exception as e:
        raise RuntimeError(f"Unable to read crosswalk at path '{path}':\n{e}")
    
    # verify
    check_pam_cw_specification(df, )
    if return_df_only: 
        return df
    
    dict_out = get_pam_dict_grouped(df, )

    return dict_out



def get_pam_dict_grouped(
    df: pd.DataFrame,
    delim_in: str = "\n",
    delim_out: str = "|",
    **kwargs,
) -> None:
    """Group the crosswalk by INF/SUP (after checking) and map each PAM suffix
        (determined by all PAMs that map to the INF/SUP group) to the group.

    Keyword Arguments
    -----------------
    delim_in : str
        Delimiter used in rows to delimit transformations
    delim_out : str
        Delimiter used in Strategies object to delimit transformations
    kwargs :
        Passed to build_pam_suffix_for_transformation()
    """

    # reduce
    df_map = (
        df[
            [
                _FIELD_PAM_ID,
                _FIELD_CW_TRANSFORMATIONS_INF, 
                _FIELD_CW_TRANSFORMATIONS_SUP
            ]
        ]
        .drop_duplicates()
        .dropna(
            how = "all",
            subset = [
                _FIELD_CW_TRANSFORMATIONS_INF, 
                _FIELD_CW_TRANSFORMATIONS_SUP,
            ]
        )
        .fillna(_BLANK, )
    )

    
    ##  BUILD THE OUTPUT MAP
    
    # initialize output dictionary
    dict_out = {}

    # group the df
    fields_group = [
        _FIELD_CW_TRANSFORMATIONS_INF, 
        _FIELD_CW_TRANSFORMATIONS_SUP
    ]
    dfg = df_map.groupby(fields_group, )
    global M
    M = df_map.copy()
    # iterate over each group to build the output dictionary
    for grp, df in dfg:
        suffix = build_pam_suffix_for_transformation(
            df[_FIELD_PAM_ID].to_numpy(),
            **kwargs,
        )
        
        grp_out = [
            x.replace(delim_in, delim_out, )
            for x in grp
        ]

        dict_out.update(
            {
                suffix: grp_out,
            }
        )

    return dict_out



def build_pam_strategies(
    strategies: 'Strategies',
    dict_pam_cw: Dict[str, List[str]],
    strategy: Union[int, str, None],
    code_prepend_inf: str = _PREFIX_EXPERIMENT_INF,
    code_prepend_sup: str = _PREFIX_EXPERIMENT_SUP,
    delim: Union[str, None] = None,
    ids: Union[None, List[int]] = None,
    sort: bool = False,
    **kwargs,
) -> Union[pd.DataFrame, None]:
    """Build strategies designed by removing transformations 1-by-1 from a 
        strategy (whirlpool--kind of the inverse of a tornado)

    Function Arguments
    ------------------
    strategies : Strategies
        Strategies object to pull from
    dict_pam_cw : Dict[str, List[str]] 
        Dictionary mapping a PAM suffix to an associated set of removal (first)
        or replacement (second) transformations
    strategy : Union[int, str, None]
        Strategy to remove transformations from
    
    Keyword Arguments
    -----------------
    code_prepend_inf : str
        Code to prepend to the strategy name to specify it is the infimum 
        (removal of associated transformations from base strategy, analogous to
        a whirlpool)
    code_prepend_sup : str
        Code to prepend to the strategy name to specify it is the supremum 
        (addition of associated transformations from base strategy, analogous to
        a tornado)
    delim : Union[str, None]
        Delimiter used to split transformation specifications
    ids : Union[None, List[int]]
        Optional specification of IDs. 
        * int:          Specify the base id explicitly. Will take the 
                        maximum between this value and max(existing_ids) + 1
        * List[int]:    Specify ids explicitly. Must be of correct length.
        * None:         Automatically start at 1 above the highest defined 
                        strategy id.
    sort : bool
        Sort the codes?
    """
    
    ##  INITIALIZE STRATEGY COMPONENTS

    strat = strategies.get_strategy(strategy, )
    if strat is None:
        return None
    
    transformations_deconstruct = strat.get_transformation_list(
        strat.transformation_specification,
        strategies.transformations,
    )

    codes = [x.code for x in transformations_deconstruct]
    if sort: codes.sort()

    delim = (
        strat.delimiter_transformation_codes
        if not isinstance(delim, str)
        else delim
    )


    ##  START BUILDING FIELDS
    
    trans_specs = []
    trans_code = []
    trans_name = []
    

    tab = strategies.attribute_table.table
    all_codes = list(tab[strategies.field_strategy_code].unique())
    all_names = list(tab[strategies.field_strategy_name].unique())

    for suffix, transf_list in dict_pam_cw.items():
        
        # some skips
        if not isinstance(suffix, str): continue
        if not isinstance(transf_list, list): continue

        # transformations to remove from the current for the "inf" run
        transformations_rm_cur = strat.get_transformation_list(
            transf_list[0],
            strategies.transformations,
        )
        transformation_codes_rm_cur = [x.code for x in transformations_rm_cur]

        # transformations to add to the current for the "sup" run
        transformations_add_cur = strat.get_transformation_list(
            transf_list[1],
            strategies.transformations,
        )
        transformation_codes_add_cur = [x.code for x in transformations_add_cur]

        dict_transformation_map = get_transformations_pivot_dict(
            transformations_rm_cur,
            transformations_add_cur,
        )


        ##  ITERATE OVER THE CODES TO BUILD NEW ONES

        added_sup = []
        codes_inf = []
        codes_sup = []

        for code in codes:

            # if not removing, just append
            if code not in transformation_codes_rm_cur:
                codes_inf.append(code)
                codes_sup.append(code)
                continue

            # otherwise, check if in map (use this to try to preserve ordering, which can be necessary)
            code_new_try = dict_transformation_map.get(code, )
            if code_new_try is not None:
                codes_sup.append(code_new_try, )
                added_sup.append(code_new_try, )
        
        """
        global added_sup1
        global codes_sup1
        global transformation_codes_add_cur1
        added_sup1 = added_sup
        codes_sup1 = codes_sup
        transformation_codes_add_cur1 = transformation_codes_add_cur
        """;

        # finally, append any un-added codes
        codes_sup.extend(
            [x for x in transformation_codes_add_cur if x not in added_sup]
        )


        ##  SET NAMES

        # infimum
        strat_code_cur_inf = build_pam_strategy_code(
            strat,
            suffix,
            _PREFIX_EXPERIMENT_INF,
        )
        strat_name_cur_inf = build_pam_strategy_name(
            strat,
            suffix,
            _PREFIX_EXPERIMENT_INF,
        )

        # supremum
        strat_code_cur_sup = build_pam_strategy_code(
            strat,
            suffix,
            _PREFIX_EXPERIMENT_SUP,
        )
        strat_name_cur_sup = build_pam_strategy_name(
            strat,
            suffix,
            _PREFIX_EXPERIMENT_SUP,
        )

        
        # extend output columns
        trans_specs.extend([delim.join(codes_inf), delim.join(codes_sup)])
        trans_code.extend([strat_code_cur_inf, strat_code_cur_sup])
        trans_name.extend([strat_name_cur_inf, strat_name_cur_sup])


    ##  BUILD IDS

    keys = strategies.attribute_table.key_values
    max_id = max(strategies.attribute_table.key_values)

    build_ids = not sf.islistlike(ids)
    if not build_ids:
        ids = [x for x in ids if x not in keys]
        build_ids = len(ids) != len(trans_specs)
    elif sf.isnumber(ids, integer = True, ):
        max_id = max(max_id, ids - 1, )
            

    ids = (
        list(range(max_id + 1, max_id + len(trans_specs) + 1))
        if build_ids
        else ids
    )


    ##  BUILD OUTPUT TABLE

    df_out = (
        pd.DataFrame( 
            {
                strategies.field_baseline_strategy: np.zeros(len(trans_specs)).astype(int),
                strategies.field_description: ["" for x in trans_specs],
                strategies.field_strategy_code: trans_code,
                strategies.field_strategy_name: trans_name,
                strategies.field_transformation_specification: trans_specs,
            }
        )
        .sort_values(by = [strategies.field_strategy_code])
        .reset_index(drop = True, )
    )

    # add IDs after sort, then set columns in correct ordder
    df_out[strategies.attribute_table.key] = ids
    df_out = df_out[strategies.attribute_table.table.columns]
            
    return df_out



def get_transformations_pivot_dict(
    transformations_list_a: List[str],
    transformations_list_b: List[str],
) -> Dict[str, List[str]]:
    """Get a dictionary to map transformations from list a to transformations
        that share the same transformer in list b. If multiple are found, no
        ordering is specified. 
    """

    dict_out = {}
    
    # get transformers in b
    transformer_codes_b = [
        x.transformer_code for x in transformations_list_b if x is not None
    ]

    # get code lists
    transformation_codes_b = [
        x.code for x in transformations_list_b if x is not None
    ]

    # iterate over those in a
    for transformation in transformations_list_a:

        # get current transformer
        code = transformation.transformer_code

        # look for matches
        w = np.where(np.array(transformer_codes_b) == code)[0]
        if len(w) > 0:
            dict_out.update(
                {
                    transformation.code: transformation_codes_b[w[0]],
                }
            )

    return dict_out

