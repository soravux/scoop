#    This file is part of DEAP.
#
#    DEAP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    DEAP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with DEAP. If not, see <http://www.gnu.org/licenses/>.

import random

from deap import algorithms
from deap import base
from deap import creator
from deap import tools
from scoop import futures

from dependency import sortingnetwork as sn
import logging
import time
import argparse
import sys

parser = argparse.ArgumentParser(description="Deap's evosn example.")
parser.add_argument('--inputs', type=int, default=6)
parser.add_argument('--cores', type=int, default=1)
parser.add_argument('--filename')
parser.add_argument('--population', type=int, default=300)
parser.add_argument('--generations', type=int, default=40)

args = parser.parse_args()
INPUTS = args.inputs




def evalEvoSN(individual, dimension):
    network = sn.SortingNetwork(dimension, individual)
    return network.assess(), network.length, network.depth

def genWire(dimension):
    return (random.randrange(dimension), random.randrange(dimension))
    
def genNetwork(dimension, min_size, max_size):
    size = random.randint(min_size, max_size)
    return [genWire(dimension) for i in range(size)]
    
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
toolbox.register("network", genNetwork, dimension=INPUTS, min_size=35, max_size=45)

# Structure initializers
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.network)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

toolbox.register("evaluate", evalEvoSN, dimension=INPUTS)
toolbox.register("mate", tools.cxTwoPoints)
toolbox.register("mutate", mutWire, dimension=INPUTS, indpb=0.05)
toolbox.register("addwire", mutAddWire, dimension=INPUTS)
toolbox.register("delwire", mutDelWire)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("map", futures.map)
#logging.warning("avant main")
def main():
    # test if file is ok before starting the test
    if args.filename:
        open(args.filename).close()
    random.seed(64)
    
    beginTime = time.time()
    evaluationTime = 0

    population = toolbox.population(n=args.population)
    #hof = tools.ParetoFront()
    
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", tools.mean)
    stats.register("std", tools.std)
    stats.register("min", min)
    stats.register("max", max)
    
    logger = tools.EvolutionLogger(["gen", "evals", "time"] + [str(k) for k in
        stats.functions.keys()])
    logger.logHeader()

    CXPB, MUTPB, ADDPB, DELPB, NGEN = 0.5, 0.2, 0.01, 0.01, args.generations
    
    evalBegin = time.time()
    # Evaluate every individuals
    fitnesses = toolbox.map(toolbox.evaluate, population)

    
    for ind, fit in zip(population, fitnesses):
        ind.fitness.values = fit

    evaluationTime += (time.time() - evalBegin)
    
    #hof.update(population)
    stats.update(population)
    
    logger.logGeneration(gen=0, evals=len(population), stats=stats, time=evaluationTime)
    
    # Begin the evolution
    for g in range(1, NGEN):
        offspring = [toolbox.clone(ind) for ind in population]
    
        # Apply crossover and mutation
        for ind1, ind2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < CXPB:
                toolbox.mate(ind1, ind2)
                del ind1.fitness.values
                del ind2.fitness.values
        
        # Note here that we have a different sheme of mutation than in the
        # original algorithm, we use 3 different mutations subsequently.
        for ind in offspring:
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
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        evalBegin = time.time()
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
        evaluationTime += (time.time() - evalBegin)
        
        population = toolbox.select(population+offspring, len(offspring))
        #hof.update(population)
        stats.update(population)
        logger.logGeneration(gen=g, evals=len(invalid_ind), stats=stats, time=evaluationTime)

    #best_network = sn.SortingNetwork(INPUTS, hof[0])
    #print(best_network)
    #print(best_network.draw())
    #print("%i errors, length %i, depth %i" % hof[0].fitness.values)
    totalTime = time.time() - beginTime
    
    print("Total time: {0}\nEvaluation time: {1}".format(totalTime, evaluationTime))
    if args.filename:
        f = open(args.filename, "a")
        f.write("{0};{1};{2};{3}\n".format(args.cores, INPUTS, totalTime, evaluationTime))
        f.close()
        
    return population, stats#, hof

if __name__ == "__main__":
    main()
