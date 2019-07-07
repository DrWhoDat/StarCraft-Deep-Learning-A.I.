import sc2
from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.player import Bot, Computer
from sc2 import position
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
 CYBERNETICSCORE, STARGATE, VOIDRAY, SCV, DRONE, ROBOTICSFACILITY, OBSERVER
import random
import cv2
import numpy as np
import os
import time
import keras

#os.environ["SC2PATH"] = 'C:/Program Files (x86)/StarCraft II/'

HEADLESS = False

class SuperStarBot(sc2.BotAI):
    def __init__(self, use_model=False):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 50
        self.do_something_after = 0
        self.use_model = use_model

        self.train_data = []
        # using model data 
        if self.use_model:
            print("USING MODEL!")
            self.model = keras.models.load_model("BasicCNN-30-epochs-0.0001-LR-4.2")

    def on_end(self, game_result):
        print('--- on_end called ---')
        print(game_result, self.use_model)

        with open("gameout-random-vs-medium.txt","a") as f:
            if self.use_model:
                f.write("Model {}\n".format(game_result))
            else:
                f.write("Random {}\n".format(game_result))

    async def on_step(self, iteration):
        self.iteration = iteration
        await self.scout()
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        await self.build_assimilators()
        await self.expand()
        await self.offensive_force_buildings()
        await self.build_offensive_force()
        await self.intel()
        await self.attack()

    def random_location_variance(self, enemy_start_location):
        x = enemy_start_location[0]
        y = enemy_start_location[1]

        #  FIXED THIS
        x += ((random.randrange(-20, 20))/100) * self.game_info.map_size[0]
        y += ((random.randrange(-20, 20))/100) * self.game_info.map_size[1]

        if x < 0:
            print("x below")
            x = 0
        if y < 0:
            print("y below")
            y = 0
        if x > self.game_info.map_size[0]:
            print("x above")
            x = self.game_info.map_size[0]
        if y > self.game_info.map_size[1]:
            print("y above")
            y = self.game_info.map_size[1]

        go_to = position.Point2(position.Pointlike((x,y)))

        return go_to

    async def scout(self):
        '''
        ['__call__', '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_game_data', '_proto', '_type_data', 'add_on_tag', 'alliance', 'assigned_harvesters', 'attack', 'build', 'build_progress', 'cloak', 'detect_range', 'distance_to', 'energy', 'facing', 'gather', 'has_add_on', 'has_buff', 'health', 'health_max', 'hold_position', 'ideal_harvesters', 'is_blip', 'is_burrowed', 'is_enemy', 'is_flying', 'is_idle', 'is_mine', 'is_mineral_field', 'is_powered', 'is_ready', 'is_selected', 'is_snapshot', 'is_structure', 'is_vespene_geyser', 'is_visible', 'mineral_contents', 'move', 'name', 'noqueue', 'orders', 'owner_id', 'position', 'radar_range', 'radius', 'return_resource', 'shield', 'shield_max', 'stop', 'tag', 'train', 'type_id', 'vespene_contents', 'warp_in']
        '''

        if len(self.units(OBSERVER)) > 0:
            scout = self.units(OBSERVER)[0]
            if scout.is_idle:
                enemy_location = self.enemy_start_locations[0]
                move_to = self.random_location_variance(enemy_location)
                print(move_to)
                await self.do(scout.move(move_to))

        else:
            for rf in self.units(ROBOTICSFACILITY).ready.noqueue:
                if self.can_afford(OBSERVER) and self.supply_left > 0:
                    await self.do(rf.train(OBSERVER))

    async def intel(self):

        # for game_info: https://github.com/Dentosal/python-sc2/blob/master/sc2/game_info.py#L162
        #print(self.game_info.map_size)
        # flip around. It's y, x when you're dealing with an array.
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)

        # UNIT: [SIZE, (BGR COLOR)]
        '''from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
 CYBERNETICSCORE, STARGATE, VOIDRAY'''
        draw_dict = {
                     NEXUS: [15, (0, 255, 0)],
                     PYLON: [3, (20, 235, 0)],
                     PROBE: [1, (55, 200, 0)],
                     ASSIMILATOR: [2, (55, 200, 0)],
                     GATEWAY: [3, (200, 100, 0)],
                     CYBERNETICSCORE: [3, (150, 150, 0)],
                     STARGATE: [5, (255, 0, 0)],
                     ROBOTICSFACILITY: [5, (215, 155, 0)],
                     #VOIDRAY: [3, (255, 100, 0)],
                    }

        for unit_type in draw_dict:
            for unit in self.units(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1)

        # NOT THE MOST IDEAL, BUT WHATEVER LOL
        main_base_names = ["nexus", "commandcenter", "hatchery"]
        for enemy_building in self.known_enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() not in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)
        for enemy_building in self.known_enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (0, 0, 255), -1)

        for enemy_unit in self.known_enemy_units:

            if not enemy_unit.is_structure:
                worker_names = ["probe",
                                "scv",
                                "drone"]
                # if that unit is a PROBE, SCV, or DRONE... it's a worker
                pos = enemy_unit.position
                if enemy_unit.name.lower() in worker_names:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (55, 0, 155), -1)
                else:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (50, 0, 215), -1)

        for obs in self.units(OBSERVER).ready:
            pos = obs.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (255, 255, 255), -1)

        for vr in self.units(VOIDRAY).ready:
            pos = vr.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (255, 100, 0), -1)

        line_max = 50
        mineral_ratio = self.minerals / 1500
        if mineral_ratio > 1.0:
            mineral_ratio = 1.0

        vespene_ratio = self.vespene / 1500
        if vespene_ratio > 1.0:
            vespene_ratio = 1.0

        population_ratio = self.supply_left / self.supply_cap
        if population_ratio > 1.0:
            population_ratio = 1.0

        plausible_supply = self.supply_cap / 200.0

        military_weight = len(self.units(VOIDRAY)) / (self.supply_cap-self.supply_left)
        if military_weight > 1.0:
            military_weight = 1.0

        cv2.line(game_data, (0, 19), (int(line_max*military_weight), 19), (250, 250, 200), 3)  # worker/supply ratio
        cv2.line(game_data, (0, 15), (int(line_max*plausible_supply), 15), (220, 200, 200), 3)  # plausible supply (supply/200.0)
        cv2.line(game_data, (0, 11), (int(line_max*population_ratio), 11), (150, 150, 150), 3)  # population ratio (supply_left/supply)
        cv2.line(game_data, (0, 7), (int(line_max*vespene_ratio), 7), (210, 200, 0), 3)  # gas / 1500
        cv2.line(game_data, (0, 3), (int(line_max*mineral_ratio), 3), (0, 255, 25), 3)  # minerals minerals/1500

        # flip horizontally to make our final fix in visual representation:
        self.flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(self.flipped, dsize=None, fx=2, fy=2)

        if not HEADLESS:
            if self.use_model:
                cv2.imshow('Model Intel', resized)
                cv2.waitKey(1)
            else:
                cv2.imshow('Random Intel', resized)
                cv2.waitKey(1)

    async def build_workers(self):
        if (len(self.units(NEXUS)) * 16) > len(self.units(PROBE)) and len(self.units(PROBE)) < self.MAX_WORKERS:
            for nexus in self.units(NEXUS).ready.noqueue:
                if self.can_afford(PROBE):
                    await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=nexuses.first)

    async def build_assimilators(self):
        for nexus in self.units(NEXUS).ready:
            vaspenes = self.state.vespene_geyser.closer_than(15.0, nexus)
            for vaspene in vaspenes:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, vaspene).exists:
                    await self.do(worker.build(ASSIMILATOR, vaspene))

    async def expand(self):
        try:
            if self.units(NEXUS).amount < (self.iteration / self.ITERATIONS_PER_MINUTE)/2 and self.can_afford(NEXUS):
                await self.expand_now()
        except Exception as e:
            print(str(e))

    async def offensive_force_buildings(self):
        if self.units(PYLON).ready.exists:
            pylon = self.units(PYLON).ready.random

            if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=pylon)

            elif len(self.units(GATEWAY)) < 1:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)

            if self.units(CYBERNETICSCORE).ready.exists:
                if len(self.units(ROBOTICSFACILITY)) < 1:
                    if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                        await self.build(ROBOTICSFACILITY, near=pylon)

            if self.units(CYBERNETICSCORE).ready.exists:
                if len(self.units(STARGATE)) < (self.iteration / self.ITERATIONS_PER_MINUTE):
                    if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
                        await self.build(STARGATE, near=pylon)

    async def build_offensive_force(self):
        for sg in self.units(STARGATE).ready.noqueue:
            if self.can_afford(VOIDRAY) and self.supply_left > 0:
                await self.do(sg.train(VOIDRAY))

    def find_target(self, state):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]

    async def attack(self):

        if len(self.units(VOIDRAY).idle) > 0:

            target = False
            if self.iteration > self.do_something_after:
                if self.use_model:
                    prediction = self.model.predict([self.flipped.reshape([-1, 176, 200, 3])])
                    choice = np.argmax(prediction[0])
                    #print('prediction: ',choice)

                    choice_dict = {0: "No Attack!",
                                   1: "Attack close to our nexus!",
                                   2: "Attack Enemy Structure!",
                                   3: "Attack Enemy Start!"}

                    print("Choice #{}:{}".format(choice, choice_dict[choice]))

                else:
                    choice = random.randrange(0, 4)


                if choice == 0:
                    # no attack
                    wait = random.randrange(20,165)
                    self.do_something_after = self.iteration + wait

                elif choice == 1:
                    #attack_unit_closest_nexus
                    if len(self.known_enemy_units) > 0:
                        target = self.known_enemy_units.closest_to(random.choice(self.units(NEXUS)))

                elif choice == 2:
                    #attack enemy structures
                    if len(self.known_enemy_structures) > 0:
                        target = random.choice(self.known_enemy_structures)

                elif choice == 3:
                    #attack_enemy_start
                    target = self.enemy_start_locations[0]

                if target:
                    for vr in self.units(VOIDRAY).idle:
                        await self.do(vr.attack(target))

                y = np.zeros(4)
                y[choice] = 1
                #print(y)
                self.train_data.append([y,self.flipped])

            #print(len(self.train_data))

for i in range(100):
    run_game(maps.get("AbyssalReefLE"), [
        Bot(Race.Protoss, SuperStarBot(use_model=True)),
        Computer(Race.Protoss, Difficulty.Medium),
        ], realtime=False)