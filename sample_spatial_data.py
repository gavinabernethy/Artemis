# generates sample spatial networks and habitat data in .CSV files for testing
import shutil
import numpy as np
import os
import networkx  # https://networkx.org/documentation/stable/reference/generators.html
import random
from cluster_functions import cluster_next_element

# ----------------------------- FOLDER PREPARATION ----------------------- #

def save_array(file, print_array):
    with open(file, mode='w') as f:
        np.savetxt(f, print_array, delimiter=', ', newline='\n', fmt='%.20f')


def check_and_create_directory(test_set, dir_path, can_overwrite_existing_dataset):
    if os.path.exists(dir_path):
        if not can_overwrite_existing_dataset:
            raise Exception("This spatial dataset already exists.")
        else:
            # overwrite: delete the existing directory then re-create a fresh empty directory
            print(f"Test set {test_set} already existed - deleting previous files and clearing directory.")
            shutil.rmtree(dir_path)
            os.makedirs(dir_path)
    else:
        os.makedirs(dir_path)


def create_description_file(desc, dir_path):
    with open(file=f'{dir_path}/description.txt', mode='w') as f:
        f.write(desc)


# ----------------------------- CONSTRUCTING THE SPATIAL NETWORK ----------------------- #

# THIS HAPPENS FIRST, AS SOME OTHER PROPERTIES MAY DEPEND ON POSITION AND ADJACENCY
def generate_patch_position_adjacency(num_patches, graph_para):
    # Automatically place them in a rectangular grid
    num_rows = int(np.ceil(np.sqrt(num_patches)))
    num_columns = int(np.ceil(num_patches / num_rows))
    position_array = np.zeros([num_patches, 2])
    for patch in range(num_patches):
        x = np.mod(patch, num_columns)
        y = np.floor(patch / num_columns)
        position_array[patch, 0] = x
        position_array[patch, 1] = y

    # Now adjacency
    graph_type = graph_para["GRAPH_TYPE"]
    adjacency_array = np.zeros([num_patches, num_patches])
    adjacency_spec = graph_para["ADJACENCY_MANUAL_SPEC"]
    if graph_type == "manual":
        # the "ADJACENCY_MANUAL_SPEC" should be a list (length = num_patches) of lists (length = num_patches)
        if adjacency_spec is not None and type(adjacency_spec) == list and len(adjacency_spec) == num_patches:
            # check dimensions and values and that the result is a symmetric matrix
            for x in range(num_patches):
                if type(adjacency_spec[x]) == list and len(adjacency_spec[x]) == num_patches:
                    for y in range(num_patches):
                        if adjacency_spec[x][y] not in [0, 1]:
                            raise Exception("Error in graph_para['ADJACENCY_MANUAL_SPEC']. "
                                            "Values should only be '0' or '1'.")
                        if adjacency_spec[x][y] != adjacency_spec[y][x]:
                            raise Exception("Error in graph_para['ADJACENCY_MANUAL_SPEC']. Matrix is not symmetric.")
                else:
                    raise Exception(f"Error in graph_para['ADJACENCY_MANUAL_SPEC']. Row {x} is not a list with "
                                    f"the correct number of columns.")
                if adjacency_spec[x][x] != 1:
                    raise Exception("Error in graph_para['ADJACENCY_MANUAL_SPEC']. Diagonals should all be 1 unless the"
                                    " patch is removed.")
            # convert list of lists from the parameters to an array
            adjacency_array = np.asarray(adjacency_spec)
        else:
            raise Exception("Error in graph_para['ADJACENCY_MANUAL_SPEC']. Incorrect number of rows.")
    else:
        # check that user was not attempting to manually specify adjacency and forgot to set the graph type
        if adjacency_spec is not None and type(adjacency_spec) == list and len(adjacency_spec) != 0:
            raise Exception("Check that graph type is `manual' or clear the manual adjacency specification.")

        if graph_type == "lattice":
            for x in range(num_patches):
                for y in range(num_patches):
                    is_suitable = False

                    # include diagonals?
                    if graph_para["IS_LATTICE_INCLUDE_DIAGONALS"]:
                        test_distance = 1.999
                    else:
                        test_distance = 1.001
                    # check regular within-grid adjacency
                    if np.linalg.norm(np.array([position_array[x, 0] - position_array[y, 0],
                                                position_array[x, 1] - position_array[y, 1]])) < test_distance:
                        is_suitable = True

                    # wrap around?
                    if graph_para["IS_LATTICE_WRAPPED"]:
                        # we need to check the minimum distance across all the types of edges of the lattice
                        # to ensure we catch all cases (esp. when diagonals are possible), we go look at both patches
                        # and determine if we will need to check their 'modulated/wrapped' x and y values.
                        if position_array[x, 0] == num_columns - 1:
                            patch_x_x_possible = [position_array[x, 0], -1]
                        else:
                            patch_x_x_possible = [position_array[x, 0]]
                        if position_array[y, 0] == num_columns - 1:
                            patch_y_x_possible = [position_array[y, 0], -1]
                        else:
                            patch_y_x_possible = [position_array[y, 0]]

                        if position_array[x, 1] == num_rows - 1:
                            patch_x_y_possible = [position_array[x, 1], -1]
                        else:
                            patch_x_y_possible = [position_array[x, 1]]
                        if position_array[y, 1] == num_rows - 1:
                            patch_y_y_possible = [position_array[y, 1], -1]
                        else:
                            patch_y_y_possible = [position_array[y, 1]]
                        # then we look at all combinations to determine if there is a shortcut
                        min_x_dist = num_columns
                        for patch_x_x in patch_x_x_possible:
                            for patch_y_x in patch_y_x_possible:
                                min_x_dist = min(min_x_dist, np.abs(patch_x_x - patch_y_x))
                        min_y_dist = num_rows
                        for patch_x_y in patch_x_y_possible:
                            for patch_y_y in patch_y_y_possible:
                                min_y_dist = min(min_y_dist, np.abs(patch_x_y - patch_y_y))
                        if np.linalg.norm(np.array([min_x_dist, min_y_dist])) < test_distance:
                            is_suitable = True

                    if is_suitable:
                        draw = np.random.binomial(n=1, p=graph_para["LATTICE_GRAPH_CONNECTIVITY"])
                        adjacency_array[x, y] = draw
                        adjacency_array[y, x] = draw
        elif graph_type == "line":
            for x in range(num_patches):
                if x > 0:
                    adjacency_array[x - 1, x] = 1
                if x < num_patches - 1:
                    adjacency_array[x, x + 1] = 1
        elif graph_type == "star":
            # all patches only adjacent to the first patch
            for x in range(num_patches):
                adjacency_array[x, 0] = 1
                adjacency_array[0, x] = 1
        elif graph_type == "random":
            for x in range(num_patches):
                for y in range(x):
                    draw = np.random.binomial(n=1, p=graph_para["RANDOM_GRAPH_CONNECTIVITY"])
                    adjacency_array[x, y] = draw
                    adjacency_array[y, x] = draw
        elif graph_type == "small_world":
            # https://networkx.org/documentation/stable/reference/generated/
            # networkx.generators.random_graphs.watts_strogatz_graph.html
            graph = networkx.watts_strogatz_graph(n=num_patches,
                                                  k=graph_para["SMALL_WORLD_NUM_NEIGHBOURS"],
                                                  p=graph_para["SMALL_WORLD_SHORTCUT_PROBABILITY"])
            adjacency_array = networkx.to_numpy_array(graph)
            if len(graph.nodes) == 0:
                raise Exception("Small World graph failed to generate - probably unsuitable number "
                                "of neighbours for this number of patches.")

        elif graph_type == "scale_free":
            # https://networkx.org/documentation/stable/reference/generated/
            # networkx.generators.directed.scale_free_graph.html
            graph = networkx.scale_free_graph(n=num_patches)  # directed
            adjacency_array = networkx.to_numpy_array(networkx.to_undirected(graph))
            adjacency_array[adjacency_array > 1] = 1
        elif graph_type == "cluster":
            # https://networkx.org/documentation/stable/reference/generated/
            # networkx.generators.random_graphs.powerlaw_cluster_graph.html
            graph = networkx.powerlaw_cluster_graph(n=num_patches,
                                                    m=graph_para["CLUSTER_NUM_NEIGHBOURS"],
                                                    p=graph_para["CLUSTER_PROBABILITY"], )
            adjacency_array = networkx.to_numpy_array(graph)
        else:
            raise Exception("Which type of graph is the spatial network?")

    # check that adjacency array has correctly generated:
    if adjacency_array.shape[0] != num_patches or adjacency_array.shape[1] != num_patches:
        raise Exception("Graph generation process has failed to produce adjacency array of size NxN "
                        "where N is the number of patches specified.")
    else:
        # ensure every patch is always considered adjacent to itself
        for x in range(num_patches):
            adjacency_array[x, x] = 1

        # ensure that the adjacency graphs are always symmetric
        for x in range(num_patches):
            for y in range(num_patches):
                if adjacency_array[x, y] == 1:
                    adjacency_array[y, x] = 1

    return adjacency_array, position_array


def generate_patch_quality(num_patches, adjacency_array, position_array, graph_para):
    quality_type = graph_para["QUALITY_TYPE"]
    max_quality = graph_para["MAX_QUALITY"]
    min_quality = graph_para["MIN_QUALITY"]
    if max_quality < min_quality or max_quality > 1.0 or min_quality < 0.0:
        raise Exception("Max and min quality parameters not as expected in [0, 1].")
    #
    # quality types are {'manual', 'random', 'auto_correlation', 'gradient'}
    if quality_type == "manual":
        # the "QUALITY_MANUAL_SPEC" should be a list of length = num_patches
        quality_spec = graph_para["QUALITY_MANUAL_SPEC"]
        if quality_spec is not None and type(quality_spec) == list and len(quality_spec) == num_patches:
            quality_array = np.zeros(shape=(num_patches, 1))
            for patch_num in range(num_patches):
                patch_quality = quality_spec[patch_num]
                # check valid
                if 0.0 <= patch_quality <= 1.0:
                    quality_array[patch_num] = patch_quality
                else:
                    raise Exception("Unsuitable patch quality is specified.")
        else:
            raise Exception("Error in the expected manual specification of patch quality (QUALITY_MANUAL_SPEC)")
    elif quality_type == "random":
        quality_array = min_quality + np.random.rand(num_patches, 1) * (max_quality - min_quality)
    elif quality_type == "auto_correlation":
        auto_correlation = graph_para["QUALITY_SPATIAL_AUTO_CORRELATION"]
        quality_array = np.zeros(shape=(num_patches, 1))
        # initial value:
        quality_array[0, 0] = np.random.rand()
        for patch in range(1, num_patches):
            # construct mean
            num_neighbours = 0
            quality_sum = 0.0
            # iterate over those neighbors who have already been assigned their quality
            for other_patch in range(patch):
                if adjacency_array[patch, other_patch] == 1:
                    num_neighbours += 1
                    quality_sum += quality_array[other_patch, 0]
            draw = np.random.rand()
            if num_neighbours > 0:
                quality_mean = quality_sum / float(num_neighbours)
                temp_value = draw + auto_correlation * (quality_mean - draw)
                # auto_corr = 0 => draw
                # auto_corr = 1 => mean
                # auto_corr = -1 => 2 draw - mean (i.e. same distance on other side of draw)
            else:
                temp_value = draw
            # check against max and min
            quality_array[patch, 0] = min(max(min_quality, temp_value), max_quality)
    elif quality_type == "gradient":
        if num_patches == 1:
            quality_array = min_quality + np.random.rand(1, 1) * (max_quality - min_quality)
        else:
            fluctuation = graph_para["QUALITY_FLUCTUATION"]
            axis = graph_para["QUALITY_AXIS"]  # x, y, x+y
            if axis == "x":
                value_vector = position_array[:, 0]
            elif axis == "y":
                value_vector = position_array[:, 1]
            elif axis == "x+y":
                value_vector = position_array[:, 0] + position_array[:, 1]
            else:
                raise Exception("Axis not chosen correctly.")
            min_pos = np.amin(value_vector)
            max_pos = np.amax(value_vector)
            if max_pos == min_pos:
                raise Exception("No variation along the axis specified.")
            else:
                quality_array = np.zeros(shape=(num_patches, 1))
                for patch in range(0, num_patches):
                    quality_array[patch, 0] = min(1.0, max(0.0, min_quality + (value_vector[patch] - min_pos) *
                                                           (max_quality - min_quality) / (max_pos - min_pos) +
                                                           fluctuation * np.random.rand()))
    else:
        raise Exception("Which type of scheme is used for patch quality in the spatial network?")
    return quality_array


def generate_patch_size(num_patches, min_patch_size, max_patch_size, graph_para):
    specified_size_list = graph_para["PATCH_SIZE_MANUAL_SPEC"]
    if specified_size_list is not None and len(specified_size_list) == num_patches:
        # in this case we have manually specified the patch sizes as a list
        patch_size_array = np.zeros(shape=(num_patches, 1))
        for patch_num in range(num_patches):
            # check is valid:
            patch_size = specified_size_list[patch_num]
            if 0.0 <= patch_size <= 1.0:
                patch_size_array[patch_num, 0] = patch_size
            else:
                raise Exception("Unsuitable patch size is specified.")
    elif specified_size_list is None:
        # otherwise generate sizes randomly
        patch_size_array = min_patch_size + (max_patch_size - min_patch_size) * np.random.rand(num_patches, 1)
    else:
        raise Exception("The graph_para option 'PATCH_SIZE_MANUAL_SPEC' should be either None or a list of length"
                        " equal to the number of patches.")
    return patch_size_array


def generate_habitat_type(generated_habitat_set, num_patches, generated_habitat_probabilities, adjacency_array,
                          is_clusters, is_chess_bind_habitat_to_size, cluster_size, cluster_type_str,
                          position_array, graph_para):
    actual_habitat_list = list(generated_habitat_set)  # needs to be ordered for weighting the probability vector
    actual_num_habitats = len(actual_habitat_list)
    auto_correlation = graph_para["HABITAT_SPATIAL_AUTO_CORRELATION"]
    is_habitat_probability_rebalanced = graph_para["IS_HABITAT_PROBABILITY_REBALANCED"]
    habitat_array = np.zeros(shape=(num_patches, 1))

    if is_clusters:
        # In this case, we build clusters of the required size using cluster_functions.cluster_next_element()
        # From a choice of box, star, chain, or also (not useful for this application) random or disconnected.
        #
        if cluster_type_str == "chess_box":
            # if selected, we draw possibles using "box" type but impose additional selection criteria in this function
            # which try to replicate a chessboard design.
            cluster_type_str = "box"
            is_chess = True
        else:
            is_chess = False

        unassigned_patches = [x for x in range(num_patches)]
        cluster_habitat_num = -1
        cluster_size_num = 0
        cluster_min_x = 0
        previous_min_x = 0

        # if cluster_size is a single value, convert to an equivalent list:
        if is_chess_bind_habitat_to_size:
            # if we have required the cluster sizes to correspond to given habitat types, check that condition here
            # but note this ONLY applies as a sub-option for chess_box.
            if is_chess and type(cluster_size) == list and len(cluster_size) == actual_num_habitats:
                cluster_size_list = cluster_size
            else:
                raise Exception("Habitat cluster options do not match: IS_CHESS_BIND_HABITAT_TO_SIZE is True, so we "
                                "need type CHESS_BOX, and length of cluster size list should match size of "
                                "main_para[INITIAL_HABITAT_SET].")
        else:
            if type(cluster_size) == int:
                cluster_size_list = [cluster_size]
            elif type(cluster_size) == list:
                cluster_size_list = cluster_size
            else:
                raise Exception("Wrong input form for habitat cluster size - should be single integer, or a list.")

        while len(unassigned_patches) > 0:
            # note that this does not need to be "< cluster_size" as the fail-mechanisms here will also cover the
            # remainder patches that need to be assigned

            # draw first patch in each cluster, then get the rest from repeated calls to cluster_next_element()
            if is_chess:
                # for chessboard, draw the lowest numbered patch - i.e. we fill from the lower-left of the lattice
                draw_num = unassigned_patches[0]
            else:
                # draw first patch in each cluster randomly
                draw_num = random.choice(unassigned_patches)
            current_cluster = [draw_num]
            unassigned_patches.remove(draw_num)  # not occurring within a loop over unassigned_patches strictly

            while len(current_cluster) < cluster_size_list[cluster_size_num]:
                # draw next elements
                possible_nums = cluster_next_element(adjacency_matrix=adjacency_array,
                                                patch_list=None,
                                                current_cluster=current_cluster,
                                                actual_patch_nums=unassigned_patches,
                                                cluster_arch_type=cluster_type_str)
                if len(possible_nums) == 0:
                    break
                else:

                    if is_chess:
                        # these constraints try to produce cyclic clusters of habitat types

                        # check if box is currently more tall than wide
                        cluster_min_x = np.min([position_array[k, 0] for k in current_cluster])
                        cluster_max_x = np.max([position_array[k, 0] for k in current_cluster])
                        cluster_min_y = np.min([position_array[k, 1] for k in current_cluster])
                        cluster_max_y = np.max([position_array[k, 1] for k in current_cluster])
                        cluster_height = cluster_max_y - cluster_min_y + 1
                        cluster_width = cluster_max_x - cluster_min_x + 1

                        # remove elements that were included due to lattice wrap
                        for possible_element in list(possible_nums):  # deliberately create a DUMMY COPY to iterate over
                            if (position_array[possible_element, 0] > cluster_max_x + 1 or
                                position_array[possible_element, 1] > cluster_max_y + 1 or
                                position_array[possible_element, 0] < cluster_min_x - 1 or
                                position_array[possible_element, 1] < cluster_min_y - 1):
                                possible_nums.remove(possible_element)

                        if len(possible_nums) == 0:
                            # break again if all possibilities removed
                            break

                        desired_height = int(np.sqrt(min(cluster_size_list)))
                        desired_width = int((cluster_size_list[cluster_size_num]) / np.sqrt(min(cluster_size_list)))
                        # check if there is a missing piece to fill in (just find the first one) due to unevenness
                        is_back_fill = False
                        back_fill_num = 0
                        for possible_num in possible_nums:
                            if position_array[possible_num, 0] < cluster_min_x:
                                is_back_fill = True
                                back_fill_num = possible_num
                                break
                        # now go through the hierarchical ruleset
                        if len(current_cluster) == 1:
                            # make taller
                            draw_num = possible_nums[-1]
                        elif is_back_fill:
                            # back fill
                            draw_num = back_fill_num
                        elif cluster_height < desired_height:
                            # make taller
                            draw_num = possible_nums[-1]
                        elif cluster_width < desired_width:
                            # make wider
                            draw_num = possible_nums[0]
                        else:
                            # check will the next random choice lead to going beyond max desired height? Prefer wider
                            next_draw_ensures_over = True
                            for possible_num in possible_nums:
                                if position_array[possible_num, 0] < cluster_max_x and position_array[
                                    possible_num, 1] < cluster_max_y:
                                    next_draw_ensures_over = False
                                    break
                            if next_draw_ensures_over:
                                draw_num = possible_nums[0]
                            else:
                                draw_num = random.choice(possible_nums)
                    else:
                        draw_num = random.choice(possible_nums)
                    current_cluster.append(draw_num)
                    unassigned_patches.remove(draw_num)  # deletion does not occur strictly within a loop over the list

            # When cluster is full size or no possible new members could be found, determine a habitat type
            first_patch_num = current_cluster[0]
            lower_y = position_array[first_patch_num, 1] - 1

            # Possibilities for IS_HABITAT_CLUSTERS:
            # - chess board, not bound, size = 1 (creates a chessboard with row offset if necessary)
            # - chess board, not bound, size > 1 (creates a chessboard but habitat types minimise border overlap)
            # - chess board, bound, size = num habitats (creates a chessboard and habitat types cycle with size)
            # - not a chess board, size = 1 (draws repeated clusters of one size, cycles habitat types)
            # - not a chess board, size > 1 (draws clusters, cycles habitat types and sizes,
            #       so set size == num habitats to bind size and habitat type and lock their cycles in phase)

            if is_chess and not is_chess_bind_habitat_to_size and  len(
                    cluster_size_list) > 1 and position_array[first_patch_num, 1] != 0:
                # But first, if it is a chessboard but we have multiple cluster sizes which are not bound to habitat
                # types, and we are not still on the first row of clusters, determine if a shift would reduce overlap:
                lower_x_list = []
                # we find the x-position of all bottom-row patches in the cluster
                for patch_clu in current_cluster:
                    if position_array[patch_clu, 1] == position_array[first_patch_num, 1]:
                        lower_x_list.append(position_array[patch_clu, 0])
                # and then we find all the patches directly beneath them and check the frequency of the habitat types
                border_habitat_frequency = np.zeros([actual_num_habitats, 1])
                for test_patch in range(first_patch_num):
                    if position_array[test_patch, 1] == lower_y and position_array[test_patch, 0] in lower_x_list:
                        border_habitat_frequency[int(habitat_array[test_patch, 0])] += 1
                # now choose (one of) the least represented habitat types, excepting the previous habitat type
                if cluster_min_x >= previous_min_x:  # (but we do allow it if there has been a ribbon reset)
                    border_habitat_frequency[cluster_habitat_num] += 9999999999.0 * int(max(cluster_size_list))
                cluster_habitat_num = random.choice(list(np.where(
                    border_habitat_frequency == np.min(border_habitat_frequency))[0]))
            else:
                # Iterate the next habitat type for the subsequent cluster
                cluster_habitat_num = np.mod(cluster_habitat_num + 1, actual_num_habitats)

                # But also check if it is a proper chessboard, and the ribbon has reset - then if an offset is required?
                if is_chess and not is_chess_bind_habitat_to_size and len(cluster_size_list) == 1:
                    if position_array[first_patch_num, 1] != 0 and cluster_min_x < previous_min_x:
                        lower_x = position_array[first_patch_num, 0]
                        for test_patch in range(first_patch_num):
                            if position_array[test_patch, 0] == lower_x and position_array[test_patch, 1] == lower_y:
                                if int(habitat_array[test_patch, 0]) == cluster_habitat_num:
                                    # iterate again!
                                    cluster_habitat_num = np.mod(cluster_habitat_num + 1, actual_num_habitats)

            # now assign all members the selected habitat type
            for patch_num in current_cluster:
                habitat_array[patch_num, 0] = cluster_habitat_num
            # finally iterate the size of the cluster
            cluster_size_num = np.mod(cluster_size_num + 1, len(cluster_size_list))
            previous_min_x = cluster_min_x

    else:
        specified_habitat_dict = graph_para["HABITAT_TYPE_MANUAL_OVERWRITE"]  # only for overwriting specific patches
        # If non-empty, this should be of the form {patch_num: habitat_type_num}, so check now for errors:
        if specified_habitat_dict is not None:
            if type(specified_habitat_dict) is not dict or len(specified_habitat_dict) > num_patches:
                raise Exception("Graph HABITAT_TYPE_MANUAL_OVERWRITE has incorrect format.")
            for key, value in specified_habitat_dict.items():
                if key < 0 or key >= num_patches or value not in actual_habitat_list:
                    raise Exception("Graph HABITAT_TYPE_MANUAL_OVERWRITE has {key: value} error.")

        specified_habitat_all_list = graph_para["HABITAT_TYPE_MANUAL_ALL_SPEC"]  # for specifying ALL patches
        if specified_habitat_all_list is not None and len(specified_habitat_all_list) == num_patches:
            # in this case we have manually specified the habitat types as a list
            for patch in range(num_patches):
                # check is valid:
                habitat_type = specified_habitat_all_list[patch]
                if habitat_type in actual_habitat_list:
                    habitat_array[patch, 0] = habitat_type
                else:
                    raise Exception("Unsuitable habitat type num is specified.")

        elif specified_habitat_all_list is None:
            # otherwise generate habitats probabilistically

            # except any manually overwritten patches
            list_of_already_assigned = []
            list_of_unassigned = [x for x in range(num_patches)]
            if specified_habitat_dict is not None and len(specified_habitat_dict) > 0:
                for manual_patch_num in specified_habitat_dict:
                    habitat_array[manual_patch_num, 0] = specified_habitat_dict[manual_patch_num]
                    list_of_already_assigned.append(manual_patch_num)
                    list_of_unassigned.remove(manual_patch_num)

            if len(actual_habitat_list) == 1:
                # if there is only one habitat type to generate from, do that here and skip the probability process
                for patch_num in list(list_of_unassigned):  # create a DUMMY LIST to iterate over
                    habitat_array[patch_num, 0] = actual_habitat_list[0]
                    list_of_already_assigned.append(patch_num)
                    list_of_unassigned.remove(patch_num)

            else:
                # base probability vector
                if generated_habitat_probabilities is not None:
                    base_probability = np.zeros(shape=(actual_num_habitats, 1))
                    for habitat_type in actual_habitat_list:
                        base_probability[habitat_type, 0] = generated_habitat_probabilities[habitat_type]
                else:
                    # uniform
                    base_probability = np.ones(shape=(actual_num_habitats, 1))
                # normalise
                norm_base_probability = normalise_matrix(base_probability)

                # while there are patches still to assign a habitat type to...
                while len(list_of_unassigned) > 0:

                    # select a unassigned patch number totally at random (i.e. uniform probability)
                    patch_num = np.random.choice(list_of_unassigned)

                    # construct probability arrays of existing distributions
                    neighbour_probability = np.zeros(shape=(actual_num_habitats, 1))
                    existing_probability = np.zeros(shape=(actual_num_habitats, 1))

                    if len(list_of_already_assigned) > 0:
                        # iterate over those patches who have already been assigned their habitats
                        for other_patch in list_of_already_assigned:
                            # only those already assigned habitats
                            if adjacency_array[patch_num, other_patch] == 1:
                                # neighbours
                                neighbour_probability[actual_habitat_list.index(
                                    int(habitat_array[other_patch, 0])), 0] += 1
                            if is_habitat_probability_rebalanced:
                                # all patches
                                existing_probability[actual_habitat_list.index(
                                    int(habitat_array[other_patch, 0])), 0] += 1

                        # normalise the previous-patch-weighted distribution (so that auto-correlation is independent of
                        # the number of neighbouring patches that have already been assigned their habitat types)
                        norm_neighbour_probability = normalise_matrix(neighbour_probability)

                        # are the base probabilities adaptive?
                        if is_habitat_probability_rebalanced:
                            total_assigned = np.sum(existing_probability)
                            anti_probability = np.zeros(shape=(actual_num_habitats, 1))
                            for habitat_type in range(actual_num_habitats):
                                anti_probability[habitat_type, 0] = (1.0 - existing_probability[habitat_type, 0]
                                                                     / total_assigned)\
                                                                    * norm_base_probability[habitat_type, 0]
                            norm_mod_base_probability = normalise_matrix(anti_probability)
                        else:
                            norm_mod_base_probability = norm_base_probability

                        # if neighbours, then weight neighbour consideration by (possibly modified) base probability
                        final_neighbour_probability = np.zeros(shape=(actual_num_habitats, 1))
                        if np.sum(norm_neighbour_probability) != 0.0:
                            for habitat_type in range(actual_num_habitats):
                                final_neighbour_probability[habitat_type, 0
                                ] = norm_neighbour_probability[habitat_type, 0] * norm_mod_base_probability[
                                    habitat_type, 0]
                            final_neighbour_probability = normalise_matrix(final_neighbour_probability)

                        # combine both parts and weight by auto-correlation and complement respectively
                        combined_probability = auto_correlation * final_neighbour_probability + (
                                1.0 - auto_correlation) * norm_mod_base_probability

                        # check if negative entries
                        norm_combined_probability = np.zeros(shape=(actual_num_habitats, 1))
                        for habitat_type in range(actual_num_habitats):
                            norm_combined_probability[habitat_type, 0] = max(0.0, combined_probability[habitat_type, 0])

                        # then re-normalise but reset to the (modified) base probability if zero
                        if np.sum(norm_combined_probability) == 0.0:
                            norm_combined_probability = norm_mod_base_probability
                        norm_combined_probability = normalise_matrix(norm_combined_probability)

                    else:
                        # this is necessary for the possibility: auto_correlation = -1 and NO patches are specified in
                        # advance, so that the first draw still defaults to the base probabilities regardless without
                        # incurring a division by zero.
                        norm_combined_probability = norm_base_probability

                    # then draw the habitat type number from this distribution
                    habitat_array[patch_num, 0] = actual_habitat_list[np.random.choice(
                        actual_num_habitats, p=np.transpose(norm_combined_probability)[0])]

                    # update status tracking
                    list_of_already_assigned.append(patch_num)
                    list_of_unassigned.remove(patch_num)  # not deleting within a loop indexed by list_of_unassigned
        else:
            raise Exception("The graph_para option 'HABITAT_TYPE_MANUAL_ALL_SPEC' should be either None or a list of"
                            " length equal to the number of patches.")
    return habitat_array


def normalise_matrix(input_matrix):
    input_sum = np.sum(input_matrix)
    if input_sum != 0.0:
        output_matrix = input_matrix / input_sum
    else:
        output_matrix = np.zeros(shape=np.shape(input_matrix))
    return output_matrix


def generate_habitat_species_scores(num_species, num_habitats, generated_spec, score_type):
    if generated_spec[score_type]["IS_SPECIES_SCORES_SPECIFIED"]:
        # The feeding or traversal scores are manually specified for each (habitat, species) pair.
        array = np.zeros([num_habitats, num_species])
        data = generated_spec[score_type]["HABITAT_SCORES"]
        if list(data.keys()) != [x for x in range(num_habitats)]:
            raise Exception(f'Error with HABITAT_SCORES: {score_type}')
        for habitat in data:
            if len(data[habitat]) != num_species:
                raise Exception(f'Error with HABITAT_SCORES: {score_type}')
            else:
                array[habitat, :] = data[habitat]
    else:
        # Otherwise generate them from the provided interval.
        min_score = generated_spec[score_type]["MIN_SCORE"]
        max_score = generated_spec[score_type]["MAX_SCORE"]
        if 0 <= min_score < max_score <= 1.0:
            array = min_score + np.random.rand(num_habitats, num_species) * (max_score - min_score)
        else:
            raise Exception(f"Maximum and minimum values of {score_type} scores not correctly ordered in [0,1]")

    return array


def generate_all_spatial_settings(is_output_files, desc, dir_path, test_set, can_overwrite_existing_dataset,
                                  num_species, num_patches, num_habitats, graph_para, generated_habitat_set,
                                  generated_habitat_probabilities, generated_spec):
    if is_output_files:
        check_and_create_directory(test_set=test_set, dir_path=dir_path,
                                   can_overwrite_existing_dataset=can_overwrite_existing_dataset)
        create_description_file(desc, dir_path=dir_path)
    adjacency_array, position_array = generate_patch_position_adjacency(num_patches=num_patches, graph_para=graph_para)
    patch_size_array = generate_patch_size(num_patches=num_patches, min_patch_size=graph_para["MIN_SIZE"],
                                           max_patch_size=graph_para["MAX_SIZE"], graph_para=graph_para)
    patch_quality_array = generate_patch_quality(num_patches=num_patches, adjacency_array=adjacency_array,
                                                 position_array=position_array, graph_para=graph_para)
    patch_habitat_array = generate_habitat_type(generated_habitat_set=generated_habitat_set, num_patches=num_patches,
                                                generated_habitat_probabilities=generated_habitat_probabilities,
                                                adjacency_array=adjacency_array,
                                                is_clusters=graph_para["IS_HABITAT_CLUSTERS"],
                                                is_chess_bind_habitat_to_size=graph_para[
                                                    "IS_CHESS_BIND_HABITAT_TO_SIZE"],
                                                cluster_size=graph_para["HABITAT_CLUSTER_SIZE"],
                                                cluster_type_str=graph_para["HABITAT_CLUSTER_TYPE_STR"],
                                                position_array=position_array,
                                                graph_para=graph_para)

    scores_dict = {}
    for score_type in ["FEEDING", "TRAVERSAL"]:
        scores_dict[score_type.lower()] = generate_habitat_species_scores(num_species=num_species,
                                                                          num_habitats=num_habitats,
                                                                          generated_spec=generated_spec,
                                                                          score_type=score_type)
    if is_output_files:
        save_array(f'{dir_path}/patch_position.csv', position_array)
        save_array(f'{dir_path}/patch_adjacency.csv', adjacency_array)
        save_array(f'{dir_path}/patch_size.csv', patch_size_array)
        save_array(f'{dir_path}/patch_quality.csv', patch_quality_array)
        save_array(f'{dir_path}/patch_habitat_type.csv', patch_habitat_array)
        save_array(f'{dir_path}/habitat_species_feeding.csv', scores_dict["feeding"])
        save_array(f'{dir_path}/habitat_species_traversal.csv', scores_dict["traversal"])

    return position_array, adjacency_array, patch_size_array, patch_quality_array, \
        patch_habitat_array, scores_dict["feeding"], scores_dict["traversal"]


# ---------------------- EXECUTE ---------------------- #

def run_sample_spatial_data(parameters, is_output_files=False):
    test_set = parameters["graph_para"]["SPATIAL_TEST_SET"]
    description = parameters["graph_para"]["SPATIAL_DESCRIPTION"]
    can_overwrite_existing_dataset = True
    dir_path = f'spatial_data_files/test_{test_set}'

    print(f"Beginning generation of spatial network {test_set}.")
    # check the habitats
    master_habitat_types_set = parameters["main_para"]["HABITAT_TYPES"]
    for habitat_num in parameters["main_para"]["INITIAL_HABITAT_SET"]:
        if habitat_num not in master_habitat_types_set:
            raise Exception(f'Habitat type {habitat_num} to be used in generation but is not part of the global set.')
    for habitat_num in master_habitat_types_set:
        if habitat_num > len(master_habitat_types_set) or type(habitat_num) is not int:
            raise Exception(f'Habitat type {habitat_num} is not a suitable number.')
    for check_num in range(len(master_habitat_types_set)):
        if check_num not in master_habitat_types_set:
            raise Exception(f'{check_num} is missing from the global set of habitat types.')

    position_array, adjacency_array, patch_size_array, patch_quality_array, patch_habitat_array, \
        habitat_feeding_scores, habitat_traversal_scores \
        = generate_all_spatial_settings(
            is_output_files=is_output_files,
            desc=description,
            dir_path=dir_path,
            test_set=test_set,
            can_overwrite_existing_dataset=can_overwrite_existing_dataset,
            num_species=len(parameters["main_para"]["SPECIES_TYPES"]),
            num_patches=parameters["main_para"]["NUM_PATCHES"],
            num_habitats=len(master_habitat_types_set),
            graph_para=parameters["graph_para"],
            generated_habitat_set=parameters["main_para"]["INITIAL_HABITAT_SET"],
            generated_habitat_probabilities=parameters["main_para"]["INITIAL_HABITAT_BASE_PROBABILITIES"],
            generated_spec=parameters["main_para"]["GENERATED_SPEC"],
        )
    print(f"Test set {test_set} generation complete.")
    return position_array, adjacency_array, patch_size_array, patch_quality_array, \
        patch_habitat_array, habitat_feeding_scores, habitat_traversal_scores


# # so that this method is called when the script is executed
if __name__ == '__main__':
    import sys
    import importlib
    if len(sys.argv) > 1:
        # optionally pass in an argument specifying the particular parameters_???.py file to use
        parameters_file = importlib.import_module(sys.argv[1])
    else:
        # otherwise use "parameters.py" as the default
        parameters_file = importlib.import_module("parameters")
    master_para = getattr(parameters_file, "master_para")
    run_sample_spatial_data(parameters=master_para, is_output_files=True)
