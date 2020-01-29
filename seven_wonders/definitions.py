import collections
import itertools
import random


discarded_cards = []


class Player:
    def __init__(self, name):
        self.name = name
        self.actions = []
        self.coins = 3
        self.free_to_play = []
        self.military_tokens = []
        self.played_cards = []
        self.player_i = 0
        self.resources = Resource()
        # List if resources from cards that give multiple excluding resources
        self.split_resources = []
        self.split_resources_combinations = []
        self.resources.initialize_resources()
        self.adjacent_players_i = None
        self.victory_points = dict()

    def play_a_turn(self, players, hand):
        cards = hand + [self.wonder] if not self.wonder.is_last_stage else hand
        playable_cards = {}
        # Create a dictionary of playable cards and their cost in terms of resources to buy from other players
        for card_i, card in enumerate(cards):
            can_buy_and_cost = self.can_play(card, players)
            if can_buy_and_cost is not None:
                playable_cards[card_i] = can_buy_and_cost
        action, picked_card_i, picked_card_cost = self._pick_best_move(playable_cards, cards, players)
        picked_card = cards[picked_card_i]
        if action == 'coin':
            self.resources['$'] += 3
            self.actions.append('discarded ' + picked_card.name)
            discarded_cards.append(card)
        elif action == 'wonder':
            next(self.wonder)
            # TODO minor: this won't print split resources for Alexandria
            self.actions.append('activated stage %s of the wonder %s - %s' %
                                (self.wonder.current_stage, self.wonder.name, self.wonder.resources))
            self._play_a_card(self.wonder, picked_card_cost, players)
        # Play a normal card
        else:
            self._play_a_card(picked_card, picked_card_cost, players)
            resource_to_print = str(picked_card.resources) if picked_card.resources else \
                '/'.join(picked_card.split_resources)
            self.actions.append('played %s - %s' % (picked_card.name, resource_to_print))
        print("player %s: %s" % (self.name, self.actions[-1]))
        # Pay players for trading
        if picked_card_cost:
            p1, p2 = picked_card_cost.keys()
            players[p1].resources['$'] += picked_card_cost[p1]
            players[p2].resources['$'] += picked_card_cost[p2]
        hand.pop(picked_card_i)

        # Play some wonder specials
        if self.wonder.specials['play_discarded_card']:
            for card in discarded_cards.copy():
                card.cost = Resource()
            self.wonder.specials['play_discarded_card'] = False
            if discarded_cards:
                self.play_a_turn(players, discarded_cards)
        if len(hand) == 1 and self.wonder.specials['play_seventh']:
            hand[0].cost = Resource()
            self.play_a_turn(players, hand)
        return hand, players

    def can_play(self, card, players):
        gold_cost = dict()
        missing_resources = (self.resources - card.cost).negative_items()
        if card.name in [c.name for c in self.played_cards]:
            return None
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
        # TODO critical: add support for buying from split resource cards
        adjacent_players = [players[i] for i in self.adjacent_players_i]
        gold_cost_list = []
        played_cards_names = [c.name for c in self.played_cards]
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
                    if (resource in 'TSCO' and 'West Trading Post' in played_cards_names) or \
                            (resource in 'LGP' and 'Marketplace' in played_cards_names) or \
                            self.wonder.specials['trading_post']:
                        cost_from_p1 += value
                    else:
                        cost_from_p1 += value * 2
                for resource, value in to_buy_from_p2.items():
                    if (resource in 'TSCO' and 'East Trading Post' in played_cards_names) or \
                            (resource in 'LGP' and 'Marketplace' in played_cards_names) or \
                            self.wonder.specials['trading_post']:
                        cost_from_p2 += value
                    else:
                        cost_from_p2 += value * 2
                if self.resources['$'] > cost_from_p1 + cost_from_p2:
                    gold_cost[adjacent_players[0].player_i] = cost_from_p1
                    gold_cost[adjacent_players[1].player_i] = cost_from_p2
                    gold_cost_list.append(gold_cost)

        if gold_cost_list:
            # Return the cheapest set of trades
            return sorted(gold_cost_list, key=lambda x: sum(x.values()))[0]
        return None

    def _play_a_card(self, card, gold_cost, players):
        # permanently remove the cost of cards in coin. Resources are not removed, since they reset every turn.
        self.resources['$'] -= card.cost['$'] + sum([v for v in gold_cost.values()])
        self.played_cards.append(card)
        self.free_to_play += card.gives_free

        if card.type == 'yellow':
            adjacent_players = [players[i] for i in self.adjacent_players_i]
            if card.name == 'Vineyard':
                self.resources['$'] += count_card_types('brown', adjacent_players)
            elif card.name == 'Bazaar':
                self.resources['$'] += count_card_types('gray', adjacent_players) * 2
            elif card.name == 'Haven':
                self.resources['$'] += count_card_types('brown', [self])
            elif card.name == 'Lighthouse':
                self.resources['$'] += count_card_types('yellow', [self])
            elif card.name == 'Chamber of Commerce':
                self.resources['$'] += count_card_types('gray', [self]) * 2
            elif card.name == 'Arena':
                self.resources['$'] += 3 * self.wonder.current_stage

        # Guild cards don't give any resource
        elif card.type == 'guild':
            return True

        elif card.type == 'wonder':
            # This wonder stage triggers a special ability
            if isinstance(card.resources, str):
                self.wonder.specials[card.resources] = True
                return True

        self.resources += card.resources
        if card.split_resources:
            self.split_resources.append(card.split_resources)
            self.split_resources_combinations = [Resource(''.join(resource_comb))
                                                 for resource_comb in itertools.product(*self.split_resources)]

    def _pick_best_move(self, playable_cards_i, cards, players):
        """Return the index of the card to pick and an action."""
        if self.wonder.specials['build_free_structure']:
            playable_cards_i = {i: {} for i in range(max(len(cards) - 2, 0))}
            self.wonder.specials['build_free_structure'] = False
        if not playable_cards_i:
            # -2 to avoid choosing the wonder
            return "coin", random.randint(0, max(len(cards) - 2, 0)), None
        picked_card_i = random.choice(list(playable_cards_i.keys()))
        cost = playable_cards_i[picked_card_i]
        if isinstance(cards[picked_card_i], Wonder):
            return "wonder", random.randint(0, max(len(cards) - 2, 0)), cost
        return 'play', picked_card_i, cost


class Resource(collections.Counter):
    # TODO trivial: split usable resources from the rest?
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
    def __init__(self, ld):
        self.cost = Resource(ld[0])
        self.name = ld[1].strip()
        self.split_resources = []
        self.resources = Resource()
        self.gives_free = [val.strip() for val in ld[3:5] if val]
        self.cards_per_players = [int(val.strip()) for val in ld[5:10] if val]
        self.age = int(ld[10].strip())
        self.type = ld[11].strip()
        if not (self.type == "yellow" or self.type == 'guild'):
            self._calculate_resources(ld[2])

    def _calculate_resources(self, resource):
        if '/' in resource:
            self.split_resources = resource.split('/')
        else:
            self.resources = Resource(resource)


class Wonder:
    def __init__(self, name, side, wonder_resource):
        self.name = name
        self.specials = {
            'play_discarded_card': False,
            'trading_post': False,
            'copy_guild_card': False,
            'build_free_structure': False,
            'play_seventh': False
        }
        self.is_last_stage = False
        self.gives_free = []
        self.side = side
        self.current_stage = 0
        self.split_resources = []
        self.cost = Resource()
        self.resources = wonder_resource
        self.type = 'wonder'
        # Don't change this into a card, it's similar, but quite different. Not worth.
        self.stages = [(Resource(), wonder_resource)]

    def __iter__(self):
        return self

    def __next__(self):
        stage = self.current_stage + 1
        # Last stage, hack so that the card cannot be played
        if stage == len(self.stages) - 1:
            self.is_last_stage = True
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
            self.resources = resource
        self.current_stage += 1


def count_card_types(card_type, players):
    return sum([1 for player in players for card in player.played_cards if card.type == card_type])
