from __future__ import annotations

from dataclasses import dataclass

from general.utils import Position, AxisDirection
from log.logger import  LOGGER


class MapNode:
    def __init__(self,
                 id: int,
                 pos: Position,
                 distance: tuple[float, float, float, float] = (float('inf'), float('inf'), float('inf'), float('inf')),
                 neighbours: tuple[MapNode, MapNode, MapNode, MapNode] = (None, None, None, None)
                 ):
        """

        Args:
            pos ():
            distance (): The distance to the other side [x-, x+, y-, y+]
        """
        self.id = id
        self._pos = pos
        self.neighbour = self._process_neighbour(distance, neighbours)

    def _process_neighbour(self,
                           distance: tuple[float, float, float, float],
                           neighbours: tuple[MapNode, MapNode, MapNode, MapNode]):
        neighbour = []
        directions = [AxisDirection.x_negative(), AxisDirection.x_positive(), AxisDirection.y_negative(),
                      AxisDirection.y_positive()]
        for dist, node, direction in zip(distance, neighbours, directions):
            neighbour.append(NodeNeighbor(node, direction, dist))
        return tuple(neighbour)

    def set_distance(self, distance: float, direction: AxisDirection):
        if not isinstance(direction, AxisDirection):
            raise TypeError('direction must be an AxisDirection')
        if not direction.is_complete():
            raise ValueError('direction must be complete')

        match direction:
            case AxisDirection.x_negative():
                self.neighbour[0].distance = distance
            case AxisDirection.x_positive():
                self.neighbour[1].distance = distance
            case AxisDirection.y_negative():
                self.neighbour[2].distance = distance
            case AxisDirection.y_positive():
                self.neighbour[3].distance = distance

    def get_distance(self, direction: AxisDirection):
        if not isinstance(direction, AxisDirection):
            raise TypeError('direction must be an AxisDirection')
        if not direction.is_complete():
            raise ValueError('direction must be complete')

        match direction:
            case AxisDirection.x_negative():
                return self.neighbour[0].distance
            case AxisDirection.x_positive():
                return self.neighbour[1].distance
            case AxisDirection.y_negative():
                return self.neighbour[2].distance
            case AxisDirection.y_positive():
                return self.neighbour[3].distance

    def set_neighbour(self, node: MapNode, direction: AxisDirection):
        """
        Set the neighbour of the node in the given direction. This will also update all the neighbour's neighbour. If
        is set to True, the neighbour will be replaced. If it is set to False, it will add a new node between the neighbour
        and the current node.
        Args:
            node: The node to be set as neighbour
            direction: The direction of the neighbour
        """
        if not isinstance(direction, AxisDirection):
            raise TypeError('direction must be an AxisDirection')
        if not direction.is_complete():
            raise ValueError('direction must be complete')
        index = self._get_direction_index(direction)
        if self.neighbour[index].node is None:
            self.neighbour[index].node = node
        else:
            self._update_neighbours(direction, node)

    def _update_neighbours(self, from_direction: AxisDirection, node: MapNode):
        """
        This will update the neighbour of the current node to the new node. This will also update the neighbour's
        neighbour.
        Args:
            from_direction ():
            node ():

        Returns:
        """
        index = self._get_direction_index(from_direction)
        for i, neighbour in enumerate(self.neighbour):
            if i == index:
                continue
            if neighbour.node is not None:
                node.neighbour[i].node = neighbour.node
                neighbour.node.neighbour[self._get_direction_index(neighbour.direction.get_opposite())].node = node

    def add_neighbour(self, node: MapNode, direction: AxisDirection):
        """
        This will add the map node to the neighbour of the current node. This will also update the neighbour's neighbour.
        Args:
            node: the node to be added
            direction: the direction of the neighbour
        """
        if not isinstance(direction, AxisDirection):
            raise TypeError('direction must be an AxisDirection')
        if not direction.is_complete():
            raise ValueError('direction must be complete')
        match direction:
            case AxisDirection.x_negative():
                self.neighbour[0].node = node
            case AxisDirection.x_positive():
                self.neighbour[1].node = node
            case AxisDirection.y_negative():
                self.neighbour[2].node = node
            case AxisDirection.y_positive():
                self.neighbour[3].node = node

    def _get_direction_index(self, direction: AxisDirection):
        if not isinstance(direction, AxisDirection):
            raise TypeError('direction must be an AxisDirection')
        if not direction.is_complete():
            raise ValueError('direction must be complete')
        temp_directions = [AxisDirection.x_negative(), AxisDirection.x_positive(), AxisDirection.y_negative(),
                           AxisDirection.y_positive()]
        return temp_directions.index(direction)

    def remove_neighbour(self, direction: AxisDirection):
        """
        Remove the neighbour of the current node in the given direction. Can only remove the node if the neighbour have
        no other neighbour on the opposite side.
        """
        
        target_node = self.get_neighbour(direction).node
        if target_node is None:
            LOGGER.debug(f'No neighbour in direction {direction} to remove ({self.id}, {self.position})')
            return

        other_axis = direction.rotate_left()
        if self.get_neighbour(other_axis).node is not None or self.get_neighbour(other_axis.get_opposite()).node is not None:
            LOGGER.debug(f'Cannot remove neighbour in direction {direction}. {other_axis.axis.name} is not empty ({self.id}, {self.position})')
            return

        if target_node.get_neighbour(direction).node is not None:
            self.set_neighbour(target_node.get_neighbour(direction).node, direction)

    def get_neighbour(self, direction: AxisDirection):
        if not isinstance(direction, AxisDirection):
            raise TypeError('direction must be an AxisDirection')
        if not direction.is_complete():
            raise ValueError('direction must be complete')

        match direction:
            case AxisDirection.x_negative():
                return self.neighbour[0]
            case AxisDirection.x_positive():
                return self.neighbour[1]
            case AxisDirection.y_negative():
                return self.neighbour[2]
            case AxisDirection.y_positive():
                return self.neighbour[3]

    @property
    def position(self):
        return self._pos

    @position.setter
    def position(self, pos: Position):
        self._pos = pos


@dataclass
class NodeNeighbor:
    node: MapNode | None
    direction: AxisDirection | None
    distance: float = float('inf')

    def update_neighbor(self):
        if self.node is None:
            return
