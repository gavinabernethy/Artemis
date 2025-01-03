class Species:

    def __init__(self,
                 name=None,
                 species_num=None,
                 lifespan=0.0,
                 minimum_population_size=0.0,
                 predator_list=None,
                 resource_usage_conversion=0.0,
                 is_dispersal=False,
                 dispersal_para=None,
                 is_dispersal_path_restricted=False,
                 always_move_with_minimum=False,
                 dispersal_penalty=0.0,
                 initial_population_mechanism=None,
                 initial_population_para=None,
                 seasonal_period=None,
                 growth_function=None,
                 growth_para=None,
                 is_growth_offset=False,
                 growth_annual_duration=None,
                 growth_offset_species=None,
                 is_growth_offset_local=False,
                 growth_offset_local=None,
                 predation_para=None,
                 is_predation_only_prevents_death=False,
                 is_nonlocal_foraging=False,
                 is_foraging_path_restricted=False,
                 predation_focus_type=None,
                 is_pure_direct_impact=False,
                 pure_direct_impact_para=None,
                 is_direct_offset=False,
                 direct_annual_duration=None,
                 direct_offset_species=None,
                 direct_offset_local=None,
                 is_direct_offset_local=False,
                 direct_impact_on_me=None,
                 is_perturbs_environment=False,
                 perturbation_para=None,
                 ):

        # core:
        self.name = name
        self.species_num = species_num

        # initial:
        self.initial_population_mechanism = initial_population_mechanism
        self.initial_population_para = initial_population_para

        # growth:
        self.minimum_population_size = minimum_population_size
        self.lifespan = lifespan
        self.seasonal_period = seasonal_period
        self.resource_usage_conversion = resource_usage_conversion
        self.growth_function = growth_function
        self.growth_para = growth_para

        # growth - offset:
        self.is_growth_offset = is_growth_offset
        if growth_annual_duration is not None:
            self.growth_annual_duration = int(growth_annual_duration)
        else:
            self.growth_annual_duration = growth_annual_duration
        self.growth_vector_offset_species = growth_offset_species
        self.is_growth_offset_local = is_growth_offset_local
        self.growth_vector_offset_local = growth_offset_local

        # basic population dynamics:
        self.predator_list = predator_list

        # dispersal:
        self.is_dispersal = is_dispersal
        self.dispersal_para = dispersal_para
        self.is_dispersal_path_restricted = is_dispersal_path_restricted
        self.always_move_with_minimum = always_move_with_minimum
        self.dispersal_efficiency = 1.0 - min(0.999999999, dispersal_penalty)  # convert penalty to efficiency in [0, 1]

        # predation:
        self.predation_para = predation_para
        self.is_predation_only_prevents_death = is_predation_only_prevents_death
        self.is_nonlocal_foraging = is_nonlocal_foraging
        self.is_foraging_path_restricted = is_foraging_path_restricted
        self.predation_focus_type = predation_focus_type

        # direct impact:
        self.is_pure_direct_impact = is_pure_direct_impact
        self.pure_direct_impact_para = pure_direct_impact_para
        self.is_direct_offset = is_direct_offset
        if direct_annual_duration is not None:
            self.direct_annual_duration = int(direct_annual_duration)
        else:
            self.direct_annual_duration = direct_annual_duration
        self.direct_vector_offset_species = direct_offset_species
        self.is_direct_offset_local = is_direct_offset_local
        self.direct_vector_offset_local = direct_offset_local
        self.direct_impact_on_me = direct_impact_on_me

        # perturbation:
        self.is_perturbs_environment = is_perturbs_environment
        self.perturbation_para = perturbation_para

        # CURRENT holding values - growth:
        self.current_r_value = None

        # CURRENT holding values - foraging
        self.current_prey_dict = None
        self.current_predation_efficiency = None
        self.current_predation_focus = None
        self.current_predation_rate = None
        self.current_foraging_mobility = None
        self.current_foraging_kappa = None
        self.current_max_foraging_path_length = None
        self.current_minimum_link_strength_foraging = None

        # CURRENT holding values - dispersal
        self.current_dispersal_mobility = None
        self.current_dispersal_direction = None
        self.current_dispersal_mechanism = None
        self.current_coefficients_lists = None
        self.current_max_dispersal_path_length = None
        self.current_minimum_link_strength_dispersal = None
