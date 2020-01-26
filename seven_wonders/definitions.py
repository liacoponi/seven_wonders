import collections
import itertools
import random


class Player:
    def __init__(self, name):
        self.name = name
        self.actions = []
        self.coins = 3
        self.free_to_play = []
        self.military_tokens = 0
        self.played_cards = []
        self.player_i = 0
        self.resources = Resource()
        # List if resources from cards that give multiple excluding resources
        self.split_resources = []
        self.split_resources_combinations = []
        self.victory_points = 0
        self.resources.initialize_resources()

    def play_a_turn(self, players, deck):
        cards = deck + [self.wonder]
        playable_cards = {}
        # Create a dictionary of playable cards and their cost in terms of resources to buy from other players
        for card_i, card in enumerate(cards):
            can_buy_with_cost = self.can_play(card, players)
            if can_buy_with_cost is not None:
                playable_cards[card_i] = can_buy_with_cost
        action, picked_card_i, picked_card_cost = self._pick_best_move(playable_cards, cards, players)
        picked_card = cards[picked_card_i]
        if action == 'coin':
            self.resources['$'] += 3
            self.actions.append('discarded ' + picked_card.name)
        elif action == 'wonder':
            next(self.wonder)
            # TODO minor: this won't print split resources for Alexandria
            self.actions.append('activated stage %s of the wonder %s - %s' %
                                (self.wonder.current_stage, self.wonder.name, self.wonder.resources))
            self._play_a_card(self.wonder, picked_card_cost)
        else:
            self._play_a_card(picked_card, picked_card_cost)
            resource_to_print = str(picked_card.resources) if picked_card.resources else \
                '/'.join(picked_card.split_resources)
            self.actions.append('played %s - %s' % (picked_card.name, resource_to_print))
        print("player %s: %s" % (self.name, self.actions[-1]))
        if picked_card_cost:
            p1, p2 = picked_card_cost.keys()
            players[p1].resources['$'] += picked_card_cost[p1]
            players[p2].resources['$'] += picked_card_cost[p2]
        self.deck.pop(picked_card_i)
        return self.deck, players

    def can_play(self, card, players):
        gold_cost = dict()
        missing_resources = (self.resources - card.cost).negative_items()
        if card.name in self.free_to_play or not missing_resources:
            return gold_cost
        # Check if we can pay missing resources with any split resource combination
        resource_set_to_buy = []
        for resource_comb in self.split_resources_combinations:
            missing_resource_after = (missing_resources + resource_comb).negative_items()
            if not missing_resource_after:
                return gold_cost
            if missing_resource_after not in resource_set_to_buy:
                resource_set_to_buy.append(Resource(missing_resource_after))
        # Buy the resources from other players
        # TODO Critical: add support for buying split resources
        adjacent_players = [players[(self.player_i - 1) % len(players)],
                            players[(self.player_i + 1) % len(players)]]
        gold_cost_list = []
        for resources_to_buy in resource_set_to_buy:
            # Other players have the resources we need.
            if not (resources_to_buy + adjacent_players[0].resources + adjacent_players[1].resources).negative_items():
                # We buy semi-randomly from players. Adding a model would require too much work for little return.
                random.shuffle(adjacent_players)
                # If we were to buy from p1, whatever it's still negative in our resources is to buy from p2
                to_buy_from_p2 = abs((resources_to_buy + adjacent_players[0].resources).negative_items())
                to_buy_from_p1 = abs(to_buy_from_p2 + resources_to_buy)
                cost_from_p1 = 0
                cost_from_p2 = 0
                for resource, value in to_buy_from_p1.items():
                    # TODO Critical: add Trading posts
                    if resource in ['blabla']:
                        cost_from_p1 += value
                    else:
                        cost_from_p1 += value * 2
                for resource, value in to_buy_from_p2.items():
                    if resource in ['blabla']:
                        cost_from_p2 += value
                    else:
                        cost_from_p2 += value * 2
                if self.resources['$'] > cost_from_p1 + cost_from_p2:
                    gold_cost[adjacent_players[0].player_i] = cost_from_p1
                    gold_cost[adjacent_players[1].player_i] = cost_from_p2
                    gold_cost_list.append(gold_cost)

        if gold_cost_list:
            # TODO Major: sort by price
            return gold_cost_list[0]
        return None

    def _play_a_card(self, card, gold_cost):
        self.resources += card.resources
        if card.split_resources:
            self.split_resources.append(card.split_resources)
            self.split_resources_combinations = [Resource(''.join(resource_comb))
                                                 for resource_comb in itertools.product(*self.split_resources)]
        # permanently remove the cost of cards in coin. Resources are not removed, since they reset every turn.
        self.resources['$'] -= card.cost['$'] + sum([v for v in gold_cost.values()])
        self.played_cards.append(card)
        # Wonders don't have gives_free attribute
        try:
            self.free_to_play += card.gives_free
        except AttributeError:
            pass

    @staticmethod
    def _pick_best_move(playable_cards_i, cards, players):
        """Return the index of the card to pick and an action."""
        if not playable_cards_i:
            # -2 to avoid choosing the wonder
            return "coin", random.randint(0, len(cards) - 2), None
        picked_card_i = random.choice(list(playable_cards_i.keys()))
        cost = playable_cards_i[picked_card_i]
        if isinstance(cards[picked_card_i], Wonder):
            return "wonder", random.randint(0, len(cards) - 2), cost
        return 'play', picked_card_i, cost


class GlobalState:
    def __init__(self, players):
        self.players = [Player(player) for player in players]
        self.player_turn = 0
        self.number_of_turns = 0


class Deck:
    def __init__(self):
        pass


class Resource(collections.Counter):
    # TODO: Split usable resources from the rest?
    _resource_map = {
        '$': 'Coins',
        'T': 'Timber',
        'S': 'Stone',
        'C': 'Clay',
        'O': 'Ore',
        'L': 'Loom',
        'G': 'Glass',
        'P': 'Papyrus',
        'X': 'Military',
        '&': 'Engineering',
        '#': 'Writing',
        '@': 'Mathematics',
        'V': 'Victory Points from blue cards',
        'W': 'Victory Points from wonder'
    }

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        self.__name__ = 'Resource'

    def initialize_resources(self):
        dict.update(self, [(k, 0) for k in self._resource_map.keys()])
        self['$'] = 4

    def negative_items(self):
        # returns all negative resources
        return Resource({k: v for k, v in self.items() if v < 0})

    def validate_resource(self, other):
        if not isinstance(other, collections.Counter):
            return NotImplemented
        if not set(other.keys()) <= set(self._resource_map.keys()):
            raise ValueError(str(other.keys()) + ' are not valid resources\n')

    def __abs__(self):
        return Resource({k: abs(v) for k, v in self.items()})

    def __sub__(self, other):
        self.validate_resource(other)
        result = Resource()
        for elem in set(self) | set(other):
            result[elem] = self[elem] - other[elem]
        return result

    def __add__(self, other):
        self.validate_resource(other)
        result = Resource()
        for elem in set(self) | set(other):
            result[elem] = self[elem] + other[elem]
        return result

    def __iadd__(self, other):
        return self + other

    def __isub__(self, other):
        return self - other

    def __repr__(self):
        if not self:
            return '%s()' % self.__class__.__name__
        items = ', '.join(map('%r: %r'.__mod__, sorted(self.items(), key=str)))
        return '%s({%s})' % (self.__class__.__name__, items)

    def __str__(self):
        if not self:
            return 'None'
        items = ', '.join(map('%r: %r'.__mod__, sorted(self.items(), key=str)))
        return '{%s}' % items


class Card:
    def __init__(self, ld=False):
        self.cost = Resource(ld[0])
        self.name = ld[1].strip()
        self.resources = Resource()
        self.split_resources = []
        self.gives_free = [val.strip() for val in ld[3:5] if val]
        self.cards_per_players = [int(val.strip()) for val in ld[5:10] if val]
        self.age = int(ld[10].strip())
        self.color = ld[11].strip()
        self._calculate_resources(ld[2])

    def _calculate_resources(self, resource):
        if '/' in resource:
            self.split_resources = resource.split('/')
        else:
            self.resources = Resource(resource)


class Wonder:
    def __init__(self, name, side, wonder_resource):
        self.name = name
        self.side = side
        self.current_stage = 0
        self.split_resources = []
        self.cost = Resource()
        self.resources = wonder_resource
        # (cost, resource) -> change this into a card? No, it's similar, but quite different. Not worth.
        self.stages = [(Resource(), wonder_resource)]

    def __iter__(self):
        return self

    def __next__(self):
        stage = self.current_stage + 1
        # Last stage, hack so that the card cannot be played
        if stage == len(self.stages) - 1:
            self.cost = collections.Counter('T' * 99)
        elif stage > len(self.stages):
            raise StopIteration
        else:
            self.cost = self.stages[stage][0]
        resource = self.stages[stage][1]
        if '/' in resource:
            self.split_resources = resource.split('/')
            self.resources = Resource()
        else:
            self.split_resources = []
            self.resources += resource
        self.current_stage += 1
