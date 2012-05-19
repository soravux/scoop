#
#    This file is part of Scalable COncurrent Operations in Python (SCOOP).
#
#    SCOOP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    SCOOP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with SCOOP. If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import print_function
import sys
import random
import logging
from scoop import futures

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

try:
    from deap import algorithms
    from deap import base
    from deap import creator
    from deap import tools
except Exception as e:
    raise Exception("This test needs DEAP to be installed.")

#####################################
####### SortingNetwork Class ########
#####################################
# v SCOOP-dependant code is below v #
#####################################

try:
    from itertools import product
except ImportError:
    def product(*args, **kwds):
        pools = map(tuple, args) * kwds.get('repeat', 1)
        result = [[]]
        for pool in pools:
            result = [x+[y] for x in result for y in pool]
        for prod in result:
            yield tuple(prod)
            
class SortingNetwork(list):
    """Sorting network class.
    
    From Wikipedia : A sorting network is an abstract mathematical model
    of a network of wires and comparator modules that is used to sort a
    sequence of numbers. Each comparator connects two wires and sort the
    values by outputting the smaller value to one wire, and a larger
    value to the other.
    """
    def __init__(self, dimension, connectors = []):
        self.dimension = dimension
        for wire1, wire2 in connectors:
            self.addConnector(wire1, wire2)
    
    def addConnector(self, wire1, wire2):
        """Add a connector between wire1 and wire2 in the network."""
        if wire1 == wire2:
            return
        
        if wire1 > wire2:
            wire1, wire2 = wire2, wire1
        
        try:
            last_level = self[-1]
        except IndexError:
            # Empty network, create new level and connector
            self.append([(wire1, wire2)])
            return
        
        for wires in last_level:
            if wires[1] >= wire1 and wires[0] <= wire2:
                self.append([(wire1, wire2)])
                return
        
        last_level.append((wire1, wire2))
    
    def sort(self, values):
        """Sort the values in-place based on the connectors in the network."""
        for level in self:
            for wire1, wire2 in level:
                if values[wire1] > values[wire2]:
                    values[wire1], values[wire2] = values[wire2], values[wire1]
    
    def assess(self, cases=None):
        """Try to sort the **cases** using the network, return the number of
        misses. If **cases** is None, test all possible cases according to
        the network dimensionality.
        """
        if cases is None:
            cases = product(range(2), repeat=self.dimension)
        
        misses = 0
        ordered = [[0]*(self.dimension-i) + [1]*i for i in range(self.dimension+1)]
        for sequence in cases:
            sequence = list(sequence)
            self.sort(sequence)
            misses += (sequence != ordered[sum(sequence)])
        return misses
    
    def draw(self):
        """Return an ASCII representation of the network."""
        str_wires = [["-"]*7 * self.depth]
        str_wires[0][0] = "0"
        str_wires[0][1] = " o"
        str_spaces = []

        for i in xrange(1, self.dimension):
            str_wires.append(["-"]*7 * self.depth)
            str_spaces.append([" "]*7 * self.depth)
            str_wires[i][0] = str(i)
            str_wires[i][1] = " o"
        
        for index, level in enumerate(self):
            for wire1, wire2 in level:
                str_wires[wire1][(index+1)*6] = "x"
                str_wires[wire2][(index+1)*6] = "x"
                for i in xrange(wire1, wire2):
                    str_spaces[i][(index+1)*6+1] = "|"
                for i in xrange(wire1+1, wire2):
                    str_wires[i][(index+1)*6] = "|"
        
        network_draw = "".join(str_wires[0])
        for line, space in zip(str_wires[1:], str_spaces):
            network_draw += "\n"
            network_draw += "".join(space)
            network_draw += "\n"
            network_draw += "".join(line)
        return network_draw
    
    @property
    def depth(self):
        """Return the number of parallel steps that it takes to sort any input.
        """
        return len(self)
    
    @property
    def length(self):
        """Return the number of comparison-swap used."""
        return sum(len(level) for level in self)

        
#####################################
####### DEAP initialisation #########
#####################################
        

INPUTS = 12 if len(sys.argv) < 2 else int(sys.argv[1])

def evalEvoSN(individual, dimension):
    network = SortingNetwork(dimension, individual)
    return network.assess(), network.length, network.depth

def genWire(dimension):
    return (random.randrange(dimension), random.randrange(dimension))
    
def genNetwork(dimension, min_size, max_size):
    size = random.randint(min_size, max_size)
    return [genWire(dimension) for i in xrange(size)]
    
def mutWire(individual, dimension, indpb):
    for index, elem in enumerate(individual):
        if random.random() < indpb:
            individual[index] = genWire(dimension)      

def mutAddWire(individual, dimension):
    index = random.randint(0, len(individual))
    individual.insert(index, genWire(dimension))

def mutDelWire(individual):
    index = random.randrange(len(individual))
    del individual[index]

creator.create("FitnessMin", base.Fitness, weights=(-1.0, -1.0, -1.0))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

# Gene initializer
toolbox.register("network", genNetwork, dimension=INPUTS, min_size=9, max_size=12)

# Structure initializers
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.network)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

toolbox.register("evaluate", evalEvoSN, dimension=INPUTS)
toolbox.register("mate", tools.cxTwoPoints)
toolbox.register("mutate", mutWire, dimension=INPUTS, indpb=0.05)
toolbox.register("addwire", mutAddWire, dimension=INPUTS)
toolbox.register("delwire", mutDelWire)
toolbox.register("select", tools.selNSGA2)

def main():
    random.seed(64)

    population = toolbox.population(n=300)
    hof = tools.ParetoFront()
    
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("Avg", tools.mean)
    stats.register("Std", tools.std)
    stats.register("Min", min)
    stats.register("Max", max)
    
    toolbox.register("map", futures.map)

    CXPB, MUTPB, ADDPB, DELPB, NGEN = 0.5, 0.2, 0.01, 0.01, 20
    
    # Evaluate every individuals
    fitnesses = toolbox.map(toolbox.evaluate, population)
    for ind, fit in zip(population, fitnesses):
        ind.fitness.values = fit
    
    hof.update(population)
    stats.update(population)
    
    # Begin the evolution
    for g in xrange(NGEN):
        print("-- Generation %i --" % g)
        offsprings = [toolbox.clone(ind) for ind in population]
    
        # Apply crossover and mutation
        for ind1, ind2 in zip(offsprings[::2], offsprings[1::2]):
            if random.random() < CXPB:
                toolbox.mate(ind1, ind2)
                del ind1.fitness.values
                del ind2.fitness.values
        
        # Note here that we have a different sheme of mutation than in the
        # original algorithm, we use 3 different mutations subsequently.
        for ind in offsprings:
            if random.random() < MUTPB:
                toolbox.mutate(ind)
                del ind.fitness.values
            if random.random() < ADDPB:
                toolbox.addwire(ind)
                del ind.fitness.values
            if random.random() < DELPB:
                toolbox.delwire(ind)
                del ind.fitness.values
                
        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offsprings if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
        
        print("  Evaluated %i individuals" % len(invalid_ind))
        
        population = toolbox.select(population+offsprings, len(offsprings))
        hof.update(population)
        stats.update(population)
        print(stats)

    best_network = SortingNetwork(INPUTS, hof[0])
    print(best_network)
    print("%i errors, length %i, depth %i" % hof[0].fitness.values)
    
    return population, stats, hof

if __name__ == "__main__":
    futures.startup(main)
