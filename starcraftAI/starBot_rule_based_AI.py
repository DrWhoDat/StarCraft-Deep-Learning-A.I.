import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, CYBERNETICSCORE, STALKER, STARGATE, VOIDRAY
import random
from examples.protoss.cannon_rush import CannonRushBot

class StarBot(sc2.BotAI):
	def __init__(self):
		self.ITERATIONS_PER_MINUTE = 165
		self.MAX_WORKERS = 50

	async def on_step(self, iteration):
		self.iteration = iteration
		#self.time = (self.state.game_loop/22.4) / 60
		await self.distribute_workers()
		await self.build_workers()
		await self.build_pylons()
		await self.build_assimilators()
		await self.expand()
		await self.build_offensive_force_buildings()
		await self.build_offensive_force()
		await self.attack()

	async def build_workers(self):
		if len(self.units(PROBE)) < len(self.units(NEXUS)) * 16 and len(self.units(PROBE)) < self.MAX_WORKERS:
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
		for nexus in self.units(NEXUS).ready.noqueue:
			vaspenes = self.state.vespene_geyser.closer_than(15.0, nexus)
			for vaspene in vaspenes:
				if not self.can_afford(ASSIMILATOR):
					break
				worker = self.select_build_worker(vaspene)
				if worker is None:
					break
				if not self.units(ASSIMILATOR).closer_than(1.0, vaspene).exists:
					await self.do(worker.build(ASSIMILATOR, vaspene))
	
	async def expand(self):
		if self.units(NEXUS).amount < ((self.iteration / self.ITERATIONS_PER_MINUTE)/2) and self.can_afford(NEXUS):
			await self.expand_now()

	async def build_offensive_force_buildings(self):
		if self.units(PYLON).ready.exists:
			pylon = self.units(PYLON).ready.random
			if len(self.units(GATEWAY)) < len(self.units(NEXUS)):
				if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
					await self.build(GATEWAY, near=pylon)

			elif self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):
				if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
					await self.build(CYBERNETICSCORE, near=pylon)

			if self.units(CYBERNETICSCORE).ready.exists and len(self.units(STARGATE)) < len((self.units(NEXUS)*2)):
					if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
						await self.build(STARGATE, near=pylon)

	async def build_offensive_force(self):
		for gw in self.units(GATEWAY).ready.noqueue:
			if not self.units(STALKER).amount > ((self.units(VOIDRAY).amount)*2):
				
				if self.can_afford(STALKER) and self.supply_left > 0:
					await self.do(gw.train(STALKER))

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
		aggressive_units = {STALKER: [15, 3], VOIDRAY: [8, 1]}

		for UNIT in aggressive_units:
			if self.units(UNIT).amount > aggressive_units[UNIT][0] and self.units(UNIT).amount > aggressive_units[UNIT][1]:
				for s in self.units(UNIT).idle:
					await self.do(s.attack(self.find_target(self.state)))

			elif self.units(UNIT).amount > aggressive_units[UNIT][1]:
				if len(self.known_enemy_units) > 0:
					for s in self.units(UNIT).idle:
						await self.do(s.attack(random.choice(self.known_enemy_units)))



run_game(maps.get("AbyssalReefLE"), [
	Bot(Race.Protoss, StarBot()),
	Bot(Race.Protoss, CannonRushBot())
	], realtime=False)