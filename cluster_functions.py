import random
from logging import raiseExceptions

import numpy as np


def cluster_next_element(adjacency_matrix, patch_list, current_cluster: list,
                         actual_patch_nums: list, cluster_arch_type: str):
    # This method offers much more control on how to specify the topology of clusters to be generated.
    # It is used in:
    # - Perturbations: called only by cluster_builder()
    # - Sample_spatial_data: called by generate_habitat_type() for cluster-based variants only when specified.
    #
    # Returns the list of patches eligible to be drawn as the next element of the cluster being iteratively constructed
    # in the list current_cluster.

    type_patch_nums = []
    if cluster_arch_type == "random":
        type_patch_nums = actual_patch_nums

    elif cluster_arch_type == "star":
        # try to choose a neighbour of the initial node
        for patch_num in actual_patch_nums:
            if adjacency_matrix[current_cluster[0], patch_num] > 0 \
                    or adjacency_matrix[patch_num, current_cluster[0]] > 0:
                type_patch_nums.append(patch_num)

    elif cluster_arch_type == "chain":
        # try to choose a neighbour of the final node
        for patch_num in actual_patch_nums:
            if adjacency_matrix[current_cluster[-1], patch_num] > 0 \
                    or adjacency_matrix[patch_num, current_cluster[-1]] > 0:
                type_patch_nums.append(patch_num)

    elif cluster_arch_type == "disconnected":
        # try to choose a neighbour of None of the current nodes
        for patch_num in actual_patch_nums:
            for already_chosen_num in current_cluster:
                if adjacency_matrix[already_chosen_num, patch_num] == 0 \
                        and adjacency_matrix[patch_num, already_chosen_num] == 0:
                    type_patch_nums.append(patch_num)

    elif cluster_arch_type == "box":
        # try to choose a neighbour of multiple current nodes
        adjacency_counter = []
        for patch_num in actual_patch_nums:
            num_adjacent = 0
            for already_chosen_num in current_cluster:
                if adjacency_matrix[already_chosen_num, patch_num] > 0 \
                        or adjacency_matrix[patch_num, already_chosen_num] > 0:
                    num_adjacent += 1
            adjacency_counter.append([patch_num, num_adjacent])
        # what was the greatest adjacency?
        if len(adjacency_counter) > 0:
            max_adjacency = max([x[1] for x in adjacency_counter])
            # choose from those with greatest adjacency only
            type_patch_nums = [x[0] for x in adjacency_counter if x[1] == max_adjacency]

    elif cluster_arch_type == "position_box":
        # choose a box consisting of positionally-close patches, regardless of actual connectivity
        distance_counter = []
        for patch_num in actual_patch_nums:
            summative_distance = 0.0
            for already_chosen_num in current_cluster:
                summative_distance += np.linalg.norm(patch_list[patch_num].position
                                                     - patch_list[already_chosen_num].position)
            distance_counter.append([patch_num, summative_distance])
        # what was minimum total positional distance of any acceptable patch to the existing members of the cluster?
        min_distance = min([x[1] for x in distance_counter])
        # choose from those with the least distance only
        type_patch_nums = [x[0] for x in distance_counter if x[1] == min_distance]

    else:
        raise "Cluster arch-type not recognised."
    return type_patch_nums


def generate_fast_cluster(sub_network, size, max_attempts, admissible_elements, num_species,
                          box_uniform_state=None, is_uniform=False, is_box=False,
                          all_elements_admissible=False, initial_patch=None,
                          return_undersized_cluster=False, is_normalised=False):
    # This is a more limited, but more efficient method to generate entire clusters of the specified size.
    # Used during complexity_analysis() when we requiring rapidly drawing many 100's of clusters.

    cluster = []
    is_success = False
    num_attempts = 0
    internal_complexity = 0.0
    neighbour_dict = sub_network["neighbour_dict"]
    if is_uniform:
        if is_normalised:
            target_array = sub_network["normalised_population_arrays"][0]
        else:
            target_array = sub_network["population_arrays"][0]
    else:
        target_array = None

    # is it possible in principle?
    if size <= sub_network["num_patches"]:
        while num_attempts < max_attempts and not is_success:
            is_success = True
            num_attempts += 1

            # initialise lists
            cluster = []  # will store the row-column indices relative to the current sub_network
            potential_neighbours = []
            # initialise arrays of length equal to the possible_neighbours list
            adjacency_counter = np.array([])
            difference_sum = np.array([])
            internal_complexity = 0.0

            # loop through drawing the 1st to Nth elements of the sample
            for num_element in range(size):

                if len(potential_neighbours) > 0:
                    # for all except the first element, draw from list according to cluster criteria in arrays
                    #
                    # at the most base level, all neighbours of the cluster are eligible
                    base_score = np.ones(len(potential_neighbours))

                    # Modifiers
                    # if either is_box or is_uniform or both, need to specify implementation with box_uniform_state
                    if box_uniform_state == "balance" and is_box and is_uniform:
                        if np.max(adjacency_counter) - np.min(adjacency_counter) != 0.0:
                            adj_modifier = 1.0 + ((adjacency_counter - np.min(adjacency_counter)) /
                                            (np.max(adjacency_counter) - np.min(adjacency_counter)))
                            base_score = base_score * adj_modifier
                        if np.max(difference_sum) - np.min(difference_sum) != 0.0:
                            uni_modifier = 2.0 - ((difference_sum - np.min(difference_sum)) /
                                            (np.max(difference_sum) - np.min(difference_sum)))
                            base_score = base_score * uni_modifier
                    elif box_uniform_state == "ensure_box" and is_box:
                        # FIRST restrict to only the greatest adjacency
                        base_score = base_score * (adjacency_counter == np.max(adjacency_counter))
                        if is_uniform:
                            # if applicable, THEN further scale by the highest score (min. 1) for uniformity
                            base_score = base_score * (1.0 + np.max(difference_sum) - difference_sum)
                    elif box_uniform_state == "ensure_uniform" and is_uniform:
                        # FIRST restrict to the highest score (i.e. lowest difference) for intra-cluster uniformity
                        base_score = base_score * (difference_sum == np.min(difference_sum))
                        # note this should work, since "difference_sum" is only associated with ACTUAL candidates
                        # (i.e. it would be a problem if the vector was the length of all possible patches, with 0
                        # score for patches that are not actually eligible neighbours and no actual candidates
                        # happening to also have a score of zero - as then no real candidate would be able to match
                        # the apparent "best" minimum added complexity).
                        if is_box:
                            # if applicable, THEN further scale by the adjacency (min. 1)
                            base_score = base_score * adjacency_counter
                    else:
                        # no box or uniform restrictions/preferences
                        # check options are consistent:
                        if is_box or is_uniform:
                            raise Exception("generate_fast_cluster() has is_box or is_uniform flag but no"
                                            "box_uniform_state is specified.")
                        pass


                    # after possible modifications, draw one of the best
                    short_list = np.where(base_score == np.max(base_score))[0]
                    draw_index = np.random.choice(short_list)
                    draw_num = potential_neighbours[draw_index]
                    cluster.append(draw_num)
                    potential_neighbours.pop(draw_index)
                    adjacency_counter = np.delete(adjacency_counter, draw_index)
                    if is_uniform:
                        # update internal complexity with difference between the newly-added element and all current
                        internal_complexity += difference_sum[draw_index]
                    difference_sum = np.delete(difference_sum, draw_index)
                else:
                    if len(cluster) == 0:
                        # draw of initial element
                        if initial_patch is not None:
                            if all_elements_admissible or initial_patch in admissible_elements:
                                draw_num = initial_patch
                            else:
                                raise Exception("Initial element not admissible.")
                        else:
                            draw_num = random.choice(admissible_elements)
                        cluster.append(draw_num)
                    else:
                        # cluster has failed to attain required size
                        is_success = False
                        if not return_undersized_cluster:
                            # reset failed cluster to empty string if small cluster not acceptable
                            cluster = []
                        break

                # check the neighbours of new member (applies to first element also) and update set of possibilities
                for potential_element in neighbour_dict[draw_num]:
                    # don't consider patches already chosen!
                    if potential_element not in cluster:
                        if not all_elements_admissible:
                            if potential_element not in admissible_elements:
                                continue

                        # separate treatment required only for those who are NEW eligible neighbours
                        if potential_element not in potential_neighbours:
                            potential_neighbours.append(potential_element)
                            # increase size of all tracking arrays
                            adjacency_counter = np.pad(adjacency_counter, (0,1), mode='constant', constant_values=0)
                            difference_sum = np.pad(difference_sum, (0, 1), mode='constant', constant_values=0)
                            potential_index = len(potential_neighbours) - 1

                            # calculate difference of new neighbour to all except the newest member of the cluster
                            if is_uniform and len(cluster) > 1:
                                for cluster_member in cluster[0:-1]:
                                    difference_sum[potential_index] += determine_difference(
                                        cluster_member, potential_element, target_array, num_species)
                        else:
                            # find the existing index for this neighbour
                            potential_index = potential_neighbours.index(potential_element)

                        if is_box:
                            # for box style, must update all neighbours of the added patch with their additional
                            # adjacency, which may go from 0 to 1 (for new neighbours) or simply be incremented
                            adjacency_counter[potential_index] += 1

                # now if necessary, update ALL neighbours (including new neighbours) with ADDITIONAL difference to the
                # newly-added member of the cluster
                if is_uniform:
                    for potential_index, potential_neighbour in enumerate(potential_neighbours):
                        difference_sum[potential_index] += determine_difference(
                            cluster[-1], potential_neighbour, target_array, num_species)

    # normalise internal complexity
    if is_uniform:
        internal_complexity = internal_complexity * 4.0 / (num_species * (size ** 2 - np.mod(size, 2)))
    return cluster, is_success, internal_complexity

def determine_difference(patch_1, patch_2, target_array, num_species):
    total_difference = 0.0
    for species_index in range(num_species):
        total_difference += np.abs(target_array[patch_1, species_index] - target_array[patch_2, species_index])
    return total_difference

def draw_partition(sub_network, size, num_species, is_normalised, partition_success_threshold,
                   initial_patch=None, is_evo=False):
    # As far as possible, cluster the elements of the network into highly-uniform clusters of the given size.
    # Note that we opt for box-clusters only as this is less ambiguous in what we 'expect' to see, and it feels like
    # a more natural interpretation of the space than the visually-strange but topologically-admissible patterns that
    # *could* get detected otherwise - i.e. it seeks more obvious approximately-square 2D clusters, rather than
    # recognising two clusters joined by a long thin string as a single 'cluster' even though topologically equivalent.

    # partition consists of a numbered dictionary of cluster lists
    partition = {}
    total_patches = sub_network["num_patches"]
    elements_to_partition = [_ for _ in range(total_patches)]
    partition_lookup = np.zeros(sub_network["num_patches"])  # returns cluster of the patch
    cluster_num = 0
    total_elements_partitioned = 0
    partition_internal_complexity = []
    partition_failed_elements = 0
    partition_target_base = size * np.divmod(total_patches, size)[0]  # the amount which COULD be precisely partitioned
    partition_target = partition_success_threshold * np.floor(partition_target_base)
    cluster_init_patch = initial_patch

    while len(elements_to_partition) > 0:

        if is_evo:
            # number of attempts
            if len(elements_to_partition) > size:
                how_many_cluster_draws = 5
            else:
                how_many_cluster_draws = 1

            best_internal_complexity = float('inf')
            best_cluster = []
            best_success = False
            for try_cluster in range(how_many_cluster_draws):
                cluster_init_patch = np.random.choice(elements_to_partition)

                # generate each box cluster
                cluster, is_success, internal_complexity = generate_fast_cluster(
                    sub_network=sub_network,
                    size=size,
                    max_attempts=1,
                    admissible_elements=elements_to_partition,
                    num_species=num_species,
                    box_uniform_state="balance",  # depends on topological restrictions desired, but best results here
                    is_box=True,                  # from a balance which avoids the most 'obvious' undesirable outcomes
                    is_uniform=True,              # from either uniformity or box restrictions being ignored.
                    all_elements_admissible=False,
                    initial_patch=cluster_init_patch,
                    return_undersized_cluster=True,
                    is_normalised=is_normalised,
                )

                if is_success and internal_complexity < best_internal_complexity:
                    best_cluster = cluster
                    best_internal_complexity = internal_complexity
                    best_success = True
                elif try_cluster == 0:
                    # record the first one as a default option
                    best_cluster = cluster
                    best_internal_complexity = internal_complexity

        else:
            # generate each box cluster
            best_cluster, best_success, best_internal_complexity = generate_fast_cluster(
                sub_network=sub_network,
                size=size,
                max_attempts=1,
                admissible_elements=elements_to_partition,
                num_species=num_species,
                box_uniform_state="balance",
                # depends on topological restrictions desired, but we obtain the best results
                is_box=True,  # here from a balance which avoids the most 'obvious' undesirable outcomes
                is_uniform=True,  # from either uniformity or box restrictions being ignored.
                all_elements_admissible=False,
                initial_patch=cluster_init_patch,
                return_undersized_cluster=True,
                is_normalised=is_normalised,
            )

        # choose the best one
        if best_success:
            total_elements_partitioned += size  # how many patches put into full-size clusters so far?
            # only record internal complexity for the properly partitioned elements - i.e. so that we can give a
            # conservative estimate of how much of the system can be partitioned for a given delta
            partition_internal_complexity.append(best_internal_complexity)
        else:
            partition_failed_elements += len(best_cluster)

        for element in best_cluster:
            elements_to_partition.remove(element)
            partition_lookup[element] = cluster_num
        partition[cluster_num] = best_cluster

        if partition_failed_elements >= total_patches - partition_target:
            # cannot possibly succeed now, no point continuing
            break

        if not is_evo and len(elements_to_partition) > 0:
            # choose next largest element from the smallest in the cluster to start with if possible,
            # otherwise choose the smallest overall from those eligible
            temp_init_upper = float('inf')
            temp_init_lower = elements_to_partition[0]
            min_cluster_element = min(best_cluster)
            for element in elements_to_partition:
                temp_init_lower = min(temp_init_lower, element)
                if element > min_cluster_element:
                    temp_init_upper = min(temp_init_upper, element)
            if temp_init_upper < float('inf'):
                cluster_init_patch = int(temp_init_upper)
            else:
                cluster_init_patch = temp_init_lower

        # set up for next cluster
        cluster_num += 1

    # did we partition > required fraction of the POSSIBLE patches (with remainder zero) into clusters of required size?
    is_partition_success = (total_elements_partitioned > partition_target)
    return partition, partition_lookup, is_partition_success, partition_internal_complexity

def partition_analysis(sub_network, partition, partition_lookup, num_species, is_normalised):
    # Determine the per-species patch-mean value in each cluster, and the adjacency relationships between clusters,
    # then calculate the mean difference across neighbouring clusters.
    if is_normalised:
        target_array_str = "normalised_population_arrays"
    else:
        target_array_str = "population_arrays"

    num_clusters = len(partition)
    partition_values = {}
    partition_adjacency = np.zeros((num_clusters, num_clusters))
    for cluster_num in range(num_clusters):
        cluster = partition[cluster_num]
        cluster_species_values = {x: 0.0 for x in range(num_species)}
        for species_index in range(num_species):
            cluster_species_values[species_index] = np.mean([sub_network[target_array_str][0][
                                                                _, species_index] for _ in cluster])
        partition_values[cluster_num] = cluster_species_values

        # determine cluster adjacency in the partition
        for element in cluster:
            for neighbour in sub_network["neighbour_dict"][element]:
                neighbour_cluster = int(partition_lookup[neighbour])
                if neighbour_cluster != cluster_num:
                    partition_adjacency[cluster_num, neighbour_cluster] = 1

    # now determine min, mean, max species-averaged difference across adjacent clusters (i.e. partition complexity)
    total_difference = 0.0
    min_difference = float('inf')
    max_difference = 0.0
    num_pairs = 0
    for cluster_1 in range(num_clusters-1):
        for cluster_2 in range(cluster_1+1, num_clusters):
            if partition_adjacency[cluster_1, cluster_2] != 0:
                num_pairs += 1
                pair_difference = 0.0
                for species_index in range(num_species):
                    pair_difference += np.abs(partition_values[cluster_1][species_index
                                              ] - partition_values[cluster_2][species_index])
                spec_ave_pair_difference = pair_difference / num_species
                total_difference += spec_ave_pair_difference
                min_difference = min(min_difference, spec_ave_pair_difference)
                max_difference = max(max_difference, spec_ave_pair_difference)
    if num_pairs > 0:
        mean_difference = total_difference / num_pairs
    else:
        mean_difference = 0.0
    return min_difference, mean_difference, max_difference