theory Participant_Opacity
  imports Main
begin

section \<open>Declared SEM-230 and SEM-231 profile coordinates\<close>

datatype coordinate_revision = Declared_Coordinate

record profile_coordinates =
  model_and_carrier_coordinate :: coordinate_revision
  observer_and_audience_coordinate :: coordinate_revision
  initial_information_coordinate :: coordinate_revision
  observation_projection_coordinate :: coordinate_revision
  memory_coordinate :: coordinate_revision
  exact_cut_and_horizon_coordinate :: coordinate_revision
  active_strategy_domain_coordinate :: coordinate_revision
  supervisor_visibility_coordinate :: coordinate_revision
  policy_and_release_coordinate :: coordinate_revision
  scheduler_and_environment_coordinate :: coordinate_revision
  nondeterminism_support_coordinate :: coordinate_revision
  time_and_progress_coordinate :: coordinate_revision
  concurrency_and_order_coordinate :: coordinate_revision
  probability_posture_coordinate :: coordinate_revision

definition declared_coordinates :: profile_coordinates where
  "declared_coordinates =
    \<lparr>model_and_carrier_coordinate = Declared_Coordinate,
     observer_and_audience_coordinate = Declared_Coordinate,
     initial_information_coordinate = Declared_Coordinate,
     observation_projection_coordinate = Declared_Coordinate,
     memory_coordinate = Declared_Coordinate,
     exact_cut_and_horizon_coordinate = Declared_Coordinate,
     active_strategy_domain_coordinate = Declared_Coordinate,
     supervisor_visibility_coordinate = Declared_Coordinate,
     policy_and_release_coordinate = Declared_Coordinate,
     scheduler_and_environment_coordinate = Declared_Coordinate,
     nondeterminism_support_coordinate = Declared_Coordinate,
     time_and_progress_coordinate = Declared_Coordinate,
     concurrency_and_order_coordinate = Declared_Coordinate,
     probability_posture_coordinate = Declared_Coordinate\<rparr>"

record ('point, 'initial, 'observation, 'strategy) semantic_profile =
  profile_carrier :: "'point set"
  profile_initial_information :: "'point \<Rightarrow> 'initial"
  profile_observation :: "'point \<Rightarrow> 'observation"
  profile_strategy :: "'point \<Rightarrow> 'strategy"
  profile_strategy_domain :: "'strategy set"
  profile_declared_coordinates :: profile_coordinates

definition matching_profiles ::
    "('point, 'initial, 'observation, 'strategy) semantic_profile \<Rightarrow>
     ('point, 'initial, 'observation, 'strategy) semantic_profile \<Rightarrow> bool" where
  "matching_profiles P Q \<longleftrightarrow>
    profile_carrier P = profile_carrier Q \<and>
    profile_initial_information P = profile_initial_information Q \<and>
    profile_observation P = profile_observation Q \<and>
    profile_strategy P = profile_strategy Q \<and>
    profile_strategy_domain P = profile_strategy_domain Q \<and>
    profile_declared_coordinates P = profile_declared_coordinates Q"

lemma matching_profiles_eq:
  assumes "matching_profiles P Q"
  shows "P = Q"
  using assms by (cases P; cases Q; simp add: matching_profiles_def)

section \<open>SEM-231 information cells, knowledge, and opacity\<close>

definition information_cell where
  "information_cell P sigma x =
    {y \<in> profile_carrier P.
      profile_strategy P y = sigma \<and>
      profile_initial_information P y = profile_initial_information P x \<and>
      profile_observation P y = profile_observation P x}"

definition participant_knows where
  "participant_knows P Secret sigma x \<longleftrightarrow>
    information_cell P sigma x \<subseteq> {y \<in> profile_carrier P. Secret y}"

definition participant_opacity where
  "participant_opacity P Secret \<longleftrightarrow>
    (\<forall>sigma \<in> profile_strategy_domain P.
      \<forall>x \<in> profile_carrier P.
        profile_strategy P x = sigma \<longrightarrow> Secret x \<longrightarrow>
          (\<exists>y \<in> information_cell P sigma x. \<not> Secret y))"

theorem participant_opacity_kernel:
  "participant_opacity P Secret \<longleftrightarrow>
    (\<forall>sigma \<in> profile_strategy_domain P.
      \<forall>x \<in> profile_carrier P.
        profile_strategy P x = sigma \<longrightarrow> Secret x \<longrightarrow>
          (\<exists>y \<in> information_cell P sigma x. \<not> Secret y))"
  unfolding participant_opacity_def by simp

lemma information_cell_reflexive:
  assumes "x \<in> profile_carrier P"
      and "profile_strategy P x = sigma"
  shows "x \<in> information_cell P sigma x"
  using assms unfolding information_cell_def by simp

lemma participant_knowledge_is_factive:
  assumes "x \<in> profile_carrier P"
      and "profile_strategy P x = sigma"
      and "participant_knows P Secret sigma x"
  shows "Secret x"
  using assms unfolding participant_knows_def information_cell_def by blast

theorem participant_opacity_knowledge_characterization:
  "participant_opacity P Secret \<longleftrightarrow>
    (\<forall>sigma \<in> profile_strategy_domain P.
      \<forall>x \<in> profile_carrier P.
        profile_strategy P x = sigma \<longrightarrow> Secret x \<longrightarrow>
          \<not> participant_knows P Secret sigma x)"
  unfolding participant_opacity_def participant_knows_def information_cell_def
  by blast

section \<open>Conditional SEM-230 noninterference implication\<close>

definition eligible_predicate where
  "eligible_predicate P High_Match Secret \<longleftrightarrow>
    (\<forall>sigma \<in> profile_strategy_domain P.
      \<forall>x \<in> profile_carrier P.
        profile_strategy P x = sigma \<and> Secret x \<longrightarrow>
          (\<exists>y \<in> profile_carrier P.
            profile_strategy P y = sigma \<and>
            profile_initial_information P y = profile_initial_information P x \<and>
            \<not> Secret y \<and>
            (\<forall>z \<in> profile_carrier P.
              profile_strategy P z = sigma \<and> High_Match y z \<longrightarrow> \<not> Secret z)))"

definition policy_noninterference where
  "policy_noninterference P High_Match \<longleftrightarrow>
    (\<forall>sigma \<in> profile_strategy_domain P.
      \<forall>x \<in> profile_carrier P.
        profile_strategy P x = sigma \<longrightarrow>
          (\<forall>y \<in> profile_carrier P.
            profile_strategy P y = sigma \<and>
            profile_initial_information P y = profile_initial_information P x \<longrightarrow>
              (\<exists>z \<in> profile_carrier P.
                profile_strategy P z = sigma \<and>
                profile_initial_information P z = profile_initial_information P x \<and>
                profile_observation P z = profile_observation P x \<and>
                High_Match y z)))"

theorem matching_policy_noninterference_implies_participant_opacity:
  assumes "matching_profiles Noninterference_Profile Opacity_Profile"
      and "eligible_predicate Noninterference_Profile High_Match Secret"
      and "policy_noninterference Noninterference_Profile High_Match"
  shows "participant_opacity Opacity_Profile Secret"
proof -
  have profile_eq: "Opacity_Profile = Noninterference_Profile"
    using assms(1) matching_profiles_eq by blast
  have target: "participant_opacity Noninterference_Profile Secret"
    unfolding participant_opacity_def
  proof (intro ballI impI)
    fix sigma x
    assume sigma: "sigma \<in> profile_strategy_domain Noninterference_Profile"
    assume point: "x \<in> profile_carrier Noninterference_Profile"
    assume strategy: "profile_strategy Noninterference_Profile x = sigma"
    assume secret: "Secret x"
    from assms(2) sigma point strategy secret obtain y where y:
        "y \<in> profile_carrier Noninterference_Profile"
        "profile_strategy Noninterference_Profile y = sigma"
        "profile_initial_information Noninterference_Profile y =
          profile_initial_information Noninterference_Profile x"
        "\<not> Secret y"
        "\<forall>z \<in> profile_carrier Noninterference_Profile.
          profile_strategy Noninterference_Profile z = sigma \<and> High_Match y z
            \<longrightarrow> \<not> Secret z"
      unfolding eligible_predicate_def by blast
    from assms(3) sigma point strategy y(1-3) obtain z where z:
        "z \<in> profile_carrier Noninterference_Profile"
        "profile_strategy Noninterference_Profile z = sigma"
        "profile_initial_information Noninterference_Profile z =
          profile_initial_information Noninterference_Profile x"
        "profile_observation Noninterference_Profile z =
          profile_observation Noninterference_Profile x"
        "High_Match y z"
      unfolding policy_noninterference_def by blast
    show "\<exists>z \<in> information_cell Noninterference_Profile sigma x. \<not> Secret z"
      unfolding information_cell_def using y(5) z by blast
  qed
  show ?thesis using profile_eq target by simp
qed

section \<open>Checked invalid-promotion boundaries\<close>

definition opacity_without_noninterference_profile ::
    "(bool \<times> bool, unit, bool, unit) semantic_profile" where
  "opacity_without_noninterference_profile =
    \<lparr>profile_carrier = UNIV,
     profile_initial_information = (\<lambda>_. ()),
     profile_observation = snd,
     profile_strategy = (\<lambda>_. ()),
     profile_strategy_domain = {()},
     profile_declared_coordinates = declared_coordinates\<rparr>"

theorem opacity_does_not_imply_policy_noninterference:
  "participant_opacity opacity_without_noninterference_profile fst \<and>
   \<not> policy_noninterference opacity_without_noninterference_profile (=)"
  unfolding participant_opacity_def information_cell_def policy_noninterference_def
    opacity_without_noninterference_profile_def
  by auto

datatype pair_point = Paired_Secret | Paired_Witness | Uncovered_Secret

fun pair_observation where
  "pair_observation Paired_Secret = False"
| "pair_observation Paired_Witness = False"
| "pair_observation Uncovered_Secret = True"

fun pair_secret where
  "pair_secret Paired_Secret = True"
| "pair_secret Paired_Witness = False"
| "pair_secret Uncovered_Secret = True"

definition one_pair_profile :: "(pair_point, unit, bool, unit) semantic_profile" where
  "one_pair_profile =
    \<lparr>profile_carrier = UNIV,
     profile_initial_information = (\<lambda>_. ()),
     profile_observation = pair_observation,
     profile_strategy = (\<lambda>_. ()),
     profile_strategy_domain = {()},
     profile_declared_coordinates = declared_coordinates\<rparr>"

theorem one_equal_history_pair_is_insufficient:
  "Paired_Witness \<in> information_cell one_pair_profile () Paired_Secret \<and>
   \<not> pair_secret Paired_Witness \<and>
   \<not> participant_opacity one_pair_profile pair_secret"
  unfolding information_cell_def participant_opacity_def one_pair_profile_def
  by (auto intro!: exI[where x=Uncovered_Secret];
      metis pair_point.exhaust pair_observation.simps pair_secret.simps)

datatype release_point = Release_Secret | Release_Witness

fun release_secret where
  "release_secret Release_Secret = True"
| "release_secret Release_Witness = False"

definition pre_release_profile :: "(release_point, unit, unit, unit) semantic_profile" where
  "pre_release_profile =
    \<lparr>profile_carrier = UNIV,
     profile_initial_information = (\<lambda>_. ()),
     profile_observation = (\<lambda>_. ()),
     profile_strategy = (\<lambda>_. ()),
     profile_strategy_domain = {()},
     profile_declared_coordinates = declared_coordinates\<rparr>"

definition post_release_profile :: "(release_point, unit, bool, unit) semantic_profile" where
  "post_release_profile =
    \<lparr>profile_carrier = UNIV,
     profile_initial_information = (\<lambda>_. ()),
     profile_observation = release_secret,
     profile_strategy = (\<lambda>_. ()),
     profile_strategy_domain = {()},
     profile_declared_coordinates = declared_coordinates\<rparr>"

theorem declassification_can_change_information_and_knowledge:
  "participant_opacity pre_release_profile release_secret \<and>
   \<not> participant_knows pre_release_profile release_secret () Release_Secret \<and>
   participant_knows post_release_profile release_secret () Release_Secret \<and>
   \<not> participant_opacity post_release_profile release_secret"
proof -
  have pre_witness:
      "Release_Witness \<in> information_cell pre_release_profile () x" for x
    unfolding information_cell_def pre_release_profile_def by simp
  have pre_opacity: "participant_opacity pre_release_profile release_secret"
    unfolding participant_opacity_def
  proof (intro ballI impI)
    fix sigma x
    assume sigma_domain: "sigma \<in> profile_strategy_domain pre_release_profile"
    assume "x \<in> profile_carrier pre_release_profile"
    assume "profile_strategy pre_release_profile x = sigma"
    assume "release_secret x"
    have sigma: "sigma = ()"
      using sigma_domain unfolding pre_release_profile_def by simp
    show "\<exists>y \<in> information_cell pre_release_profile sigma x.
        \<not> release_secret y"
    proof (rule bexI[where x=Release_Witness])
      show "\<not> release_secret Release_Witness" by simp
      show "Release_Witness \<in> information_cell pre_release_profile sigma x"
        using pre_witness[of x] sigma by simp
    qed
  qed
  have pre_not_known:
      "\<not> participant_knows pre_release_profile release_secret () Release_Secret"
    unfolding participant_knows_def
  proof
    assume known:
        "information_cell pre_release_profile () Release_Secret \<subseteq>
          {y \<in> profile_carrier pre_release_profile. release_secret y}"
    have
        "Release_Witness \<in>
          {y \<in> profile_carrier pre_release_profile. release_secret y}"
      using known pre_witness[of Release_Secret] by auto
    then show False by simp
  qed
  have post_cell:
      "information_cell post_release_profile () Release_Secret = {Release_Secret}"
    unfolding information_cell_def post_release_profile_def
    by (rule set_eqI; rename_tac y; case_tac y; simp)
  have post_known:
      "participant_knows post_release_profile release_secret () Release_Secret"
    unfolding participant_knows_def
    apply (simp only: post_cell)
    unfolding post_release_profile_def
    by simp
  have post_not_opacity:
      "\<not> participant_opacity post_release_profile release_secret"
  proof
    assume opaque: "participant_opacity post_release_profile release_secret"
    have
        "\<exists>y \<in> information_cell post_release_profile () Release_Secret.
          \<not> release_secret y"
      using opaque[unfolded participant_opacity_def, rule_format, of "()" Release_Secret]
      unfolding post_release_profile_def
      by simp
    with post_cell show False by simp
  qed
  show ?thesis using pre_opacity pre_not_known post_known post_not_opacity by simp
qed

definition post_revocation_with_memory_profile ::
    "(release_point, unit, bool, unit) semantic_profile" where
  "post_revocation_with_memory_profile = post_release_profile"

theorem revocation_does_not_erase_retained_observation:
  "information_cell post_revocation_with_memory_profile () Release_Secret =
      information_cell post_release_profile () Release_Secret \<and>
   participant_knows post_revocation_with_memory_profile release_secret () Release_Secret"
  unfolding post_revocation_with_memory_profile_def
  using declassification_can_change_information_and_knowledge by simp

definition empty_step :: "release_point \<Rightarrow> release_point \<Rightarrow> bool" where
  "empty_step _ _ \<longleftrightarrow> False"

definition simulation where
  "simulation Step R \<longleftrightarrow>
    (\<forall>p q p'. R p q \<and> Step p p' \<longrightarrow>
      (\<exists>q'. Step q q' \<and> R p' q'))"

definition strong_bisimulation where
  "strong_bisimulation Step R \<longleftrightarrow>
    simulation Step R \<and> simulation Step (\<lambda>p q. R q p)"

definition singleton_secret_profile ::
    "(release_point, unit, unit, unit) semantic_profile" where
  "singleton_secret_profile =
    \<lparr>profile_carrier = {Release_Secret},
     profile_initial_information = (\<lambda>_. ()),
     profile_observation = (\<lambda>_. ()),
     profile_strategy = (\<lambda>_. ()),
     profile_strategy_domain = {()},
     profile_declared_coordinates = declared_coordinates\<rparr>"

theorem behavioral_relations_without_preservation_do_not_imply_opacity:
  "equiv UNIV Id \<and>
   simulation empty_step (=) \<and>
   strong_bisimulation empty_step (=) \<and>
   \<not> participant_opacity singleton_secret_profile release_secret"
  unfolding equiv_def refl_on_def sym_def trans_def
    simulation_def strong_bisimulation_def empty_step_def
    participant_opacity_def information_cell_def singleton_secret_profile_def
  by auto

definition coarse_observation_profile ::
    "(release_point, unit, unit, unit) semantic_profile" where
  "coarse_observation_profile = pre_release_profile"

definition stronger_observation_profile ::
    "(release_point, unit, bool, unit) semantic_profile" where
  "stronger_observation_profile = post_release_profile"

theorem untimed_individual_observation_does_not_imply_stronger_observation_opacity:
  "participant_opacity coarse_observation_profile release_secret \<and>
   \<not> participant_opacity stronger_observation_profile release_secret"
  unfolding coarse_observation_profile_def stronger_observation_profile_def
  using declassification_can_change_information_and_knowledge by simp

definition secret_weight :: "release_point \<Rightarrow> nat" where
  "secret_weight p = (if p = Release_Secret then 9 else 1)"

theorem possibilistic_opacity_does_not_imply_a_probability_bound:
  "participant_opacity coarse_observation_profile release_secret \<and>
   \<not> secret_weight Release_Secret \<le> secret_weight Release_Witness"
  unfolding coarse_observation_profile_def secret_weight_def
  using declassification_can_change_information_and_knowledge by simp

end
