# generates sample spatial networks and habitat data in .CSV files for testing
import random
import shutil

import numpy as np
import os
from parameters import master_para
import networkx  # https://networkx.org/documentation/stable/reference/generators.html

TEST_SET = master_para["graph_para"]["SPATIAL_TEST_SET"]
DESCRIPTION = master_para["graph_para"]["SPATIAL_DESCRIPTION"]
CAN_OVERWRITE_EXISTING_DATASET = True
DIR_PATH = f'spatial_data_files/test_{TEST_SET}'


# ----------------------------- FOLDER PREPARATION ----------------------- #

def save_array(file, print_array):
    with open(file, mode='w') as f:
        np.savetxt(f, print_array, delimiter=', ', newline='\n', fmt='%f')


def check_and_create_directory():
    if os.path.exists(DIR_PATH):
        if not CAN_OVERWRITE_EXISTING_DATASET:
            raise Exception("This spatial dataset already exists.")
        else:
            # overwrite: delete the existing directory then re-create a fresh empty directory
            shutil.rmtree(DIR_PATH)
            os.makedirs(DIR_PATH)
    else:
        os.makedirs(DIR_PATH)


def create_description_file(desc):
    with open(file=f'{DIR_PATH}/description.txt', mode='w') as f:
        f.write(desc)


# ----------------------------- CONSTRUCTING THE SPATIAL NETWORK ----------------------- #

# THIS HAPPENS FIRST, AS SOME OTHER PROPERTIES MAY DEPEND ON POSITION AND ADJACENCY
def generate_patch_position_and_adjacency(num_patches, graph_para):
    # Automatically place them in a rectangular grid
    num_rows = np.ceil(np.sqrt(num_patches))
    num_columns = np.ceil(num_patches / num_rows)
    position_array = np.zeros([num_patches, 2])
    for patch in range(num_patches):
        x = np.mod(patch, num_columns)
        y = np.floor(patch / num_columns)
        position_array[patch, 0] = x
        position_array[patch, 1] = y
    save_array(f'{DIR_PATH}/patch_position.csv', position_array)

    # Now adjacency
    graph_type = graph_para["GRAPH_TYPE"]
    adjacency_array = np.zeros([num_patches, num_patches])

    if graph_type == "manual":
        # the "ADJACENCY_MANUAL_SPEC" should be a list (length = num_patches) of lists (length = num_patches)
        adjacency_spec = graph_para["ADJACENCY_MANUAL_SPEC"]
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
    elif graph_type == "lattice":
        for x in range(num_patches):
            for y in range(num_patches):
                if np.linalg.norm(np.array([position_array[x, 0] - position_array[y, 0],
                                            position_array[x, 1] - position_array[y, 1]])) < 1.999:  # include diagonals
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
        # https://networkx.org/documentation/stable/reference/generated/networkx.generators.random_graphs.watts_strogatz_graph.html
        graph = networkx.watts_strogatz_graph(n=num_patches,
                                              k=graph_para["SMALL_WORLD_NUM_NEIGHBOURS"],
                                              p=graph_para["SMALL_WORLD_SHORTCUT_PROBABILITY"])
        adjacency_array = networkx.to_numpy_array(graph)
    elif graph_type == "scale_free":
        # https://networkx.org/documentation/stable/reference/generated/networkx.generators.directed.scale_free_graph.html
        graph = networkx.scale_free_graph(n=num_patches)  # directed
        adjacency_array = networkx.to_numpy_array(networkx.to_undirected(graph))
        adjacency_array[adjacency_array > 1] = 1
    elif graph_type == "cluster":
        # https://networkx.org/documentation/stable/reference/generated/networkx.generators.random_graphs.powerlaw_cluster_graph.html
        graph = networkx.powerlaw_cluster_graph(n=num_patches,
                                                m=graph_para["CLUSTER_NUM_NEIGHBOURS"],
                                                p=graph_para["CLUSTER_PROBABILITY"], )
        adjacency_array = networkx.to_numpy_array(graph)
    else:
        raise Exception("Which type of graph is the spatial network?")

    # ensure every patch is always considered adjacent to itself
    for x in range(num_patches):
        adjacency_array[x, x] = 1

    # ensure that the adjacency graphs are always symmetric
    for x in range(num_patches):
        for y in range(num_patches):
            if adjacency_array[x, y] == 1:
                adjacency_array[y, x] = 1

    save_array(f'{DIR_PATH}/patch_adjacency.csv', adjacency_array)
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
    save_array(f'{DIR_PATH}/patch_quality.csv', quality_array)


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
    save_array(f'{DIR_PATH}/patch_size.csv', patch_size_array)


def generate_habitat_type(generated_habitat_set, num_patches, generated_habitat_probabilities,
                          adjacency_array, graph_para):
    actual_habitat_list = list(generated_habitat_set)  # needs to be ordered for weighting the probability vector
    actual_num_habitats = len(actual_habitat_list)
    auto_correlation = graph_para["HABITAT_SPATIAL_AUTO_CORRELATION"]
    habitat_array = np.zeros(shape=(num_patches, 1))

    specified_habitat_list = graph_para["HABITAT_TYPE_MANUAL_SPEC"]
    if specified_habitat_list is not None and len(specified_habitat_list) == num_patches:
        # in this case we have manually specified the habitat types as a list
        for patch in range(num_patches):
            # check is valid:
            habitat_type_num = specified_habitat_list[patch]
            if habitat_type_num in actual_habitat_list:
                habitat_array[patch, 0] = habitat_type_num
            else:
                raise Exception("Unsuitable habitat type num is specified.")
    elif specified_habitat_list is None:
        # otherwise generate habitats probabilistically
        # initial value:
        habitat_array[0, 0] = int(random.choice(actual_habitat_list))
        # base probability vector
        if generated_habitat_probabilities is not None:
            base_probability = np.zeros(shape=(actual_num_habitats, 1))
            for habitat_type_num in actual_habitat_list:
                base_probability[habitat_type_num, 0] = generated_habitat_probabilities[habitat_type_num]
        else:
            # uniform
            base_probability = np.ones(shape=(actual_num_habitats, 1))
        # normalise
        normalised_base_probability = base_probability / np.sum(base_probability)
        for patch in range(1, num_patches):
            # construct probability array
            habitat_probability = np.zeros(shape=(actual_num_habitats, 1))
            # iterate over those neighbors who have already been assigned their habitats
            for other_patch in range(patch):
                if adjacency_array[patch, other_patch] == 1:
                    habitat_probability[actual_habitat_list.index(int(habitat_array[other_patch, 0])), 0] += 1

            # normalise the previous-patch-weighted distribution (so that auto-correlation is independent of the number
            # of patches that have already been assigned their habitat types)
            if np.sum(habitat_probability) != 0.0:
                normalised_habitat_probability = habitat_probability / np.sum(habitat_probability)
            else:
                normalised_habitat_probability = np.zeros(shape=(actual_num_habitats, 1))
            # combine both parts and weight by auto-correlation and complement respectively
            combined_habitat_probability = auto_correlation * normalised_habitat_probability + (
                    1.0 - auto_correlation) * normalised_base_probability
            # check if negative entries
            norm_combined_habitat_probability = np.zeros(shape=(actual_num_habitats, 1))
            for habitat_type in range(actual_num_habitats):
                norm_combined_habitat_probability[habitat_type] = max(0.0, combined_habitat_probability[habitat_type])
            # then re-normalise
            if np.sum(norm_combined_habitat_probability) == 0.0:
                norm_combined_habitat_probability = normalised_base_probability
            else:
                norm_combined_habitat_probability = norm_combined_habitat_probability / \
                                                    np.sum(norm_combined_habitat_probability)
            # then draw
            habitat_array[patch, 0] = actual_habitat_list[np.random.choice(
                actual_num_habitats, p=np.transpose(norm_combined_habitat_probability)[0])]
    else:
        raise Exception("The graph_para option 'HABITAT_TYPE_MANUAL_SPEC' should be either None or a list of length"
                        " equal to the number of patches.")
    save_array(f'{DIR_PATH}/patch_habitat_type.csv', habitat_array)


def generate_habitat_species_scores(num_species, num_habitats, generated_spec, score_type):
    if generated_spec[score_type]["IS_SPECIES_SCORES_SPECIFIED"]:
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
        array = np.random.rand(num_habitats, num_species)
    save_array(f'{DIR_PATH}/habitat_species_' + score_type.lower() + '.csv', array)


def generate_all_spatial_files(desc, num_species, num_patches, num_habitats, graph_para,
                               generated_habitat_set, generated_habitat_probabilities, generated_spec):
    check_and_create_directory()
    create_description_file(desc)
    adjacency_array, position_array = generate_patch_position_and_adjacency(num_patches=num_patches,
                                                                            graph_para=graph_para)
    generate_patch_size(num_patches=num_patches, min_patch_size=graph_para["MIN_SIZE"],
                        max_patch_size=graph_para["MAX_SIZE"], graph_para=graph_para)
    generate_patch_quality(num_patches=num_patches, adjacency_array=adjacency_array,
                           position_array=position_array, graph_para=graph_para)
    generate_habitat_type(generated_habitat_set=generated_habitat_set, num_patches=num_patches,
                          generated_habitat_probabilities=generated_habitat_probabilities,
                          adjacency_array=adjacency_array, graph_para=graph_para)
    for score_type in ["FEEDING", "TRAVERSAL"]:
        generate_habitat_species_scores(num_species=num_species, num_habitats=num_habitats,
                                        generated_spec=generated_spec, score_type=score_type)


# ---------------------- EXECUTE ---------------------- #

def run_sample_spatial_data():
    print(f"Beginning generation of spatial network {TEST_SET}.")
    # check the habitats
    master_habitat_types_set = master_para["main_para"]["HABITAT_TYPES"]
    for habitat_num in master_para["main_para"]["INITIAL_HABITAT_SET"]:
        if habitat_num not in master_habitat_types_set:
            raise Exception(f'Habitat type {habitat_num} to be used in generation but is not part of the global set.')
    for habitat_num in master_habitat_types_set:
        if habitat_num > len(master_habitat_types_set) or type(habitat_num) is not int:
            raise Exception(f'Habitat type {habitat_num} is not a suitable number.')
    for check_num in range(len(master_habitat_types_set)):
        if check_num not in master_habitat_types_set:
            raise Exception(f'{check_num} is missing from the global set of habitat types.')

    generate_all_spatial_files(
        desc=DESCRIPTION,
        num_species=len(master_para["main_para"]["SPECIES_TYPES"]),
        num_patches=master_para["main_para"]["NUM_PATCHES"],
        num_habitats=len(master_habitat_types_set),
        graph_para=master_para["graph_para"],
        generated_habitat_set=master_para["main_para"]["INITIAL_HABITAT_SET"],
        generated_habitat_probabilities=master_para["main_para"]["INITIAL_HABITAT_BASE_PROBABILITIES"],
        generated_spec=master_para["main_para"]["GENERATED_SPEC"],
    )
    print(f"Test set {TEST_SET} generation complete.")


# # so that this method is called when the script is executed
if __name__ == '__main__':
    run_sample_spatial_data()
