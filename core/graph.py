"""
Graph representation as an immutable JAX-compatible structure.

This module defines the immutable graph state that forms the foundation
of our transformation system, designed for JAX compatibility.
"""
import jax
import jax.numpy as jnp
import dataclasses
from typing import Dict, Any, Set, Tuple, Optional, TypeVar, List, Callable
from functools import partial
from dataclasses import field


class CapacityExceededError(Exception):
    """Raised when trying to add more nodes than capacity allows."""
    pass


@jax.tree_util.register_pytree_node_class
@dataclasses.dataclass(frozen=True)
class GraphState:
    """
    Immutable JAX-compatible graph state representation.

    This class represents a complete graph state with node attributes,
    edge attributes, adjacency matrices, and global attributes. It's designed
    to be immutable and compatible with JAX transformations.
    """
    node_types: jnp.ndarray

    node_attrs: Dict[str, jnp.ndarray]
    adj_matrices: Dict[str, jnp.ndarray]
    edge_attrs: Dict[str, jnp.ndarray] = field(default_factory=dict)
    global_attrs: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Ensure edge_attrs is initialized
        if self.edge_attrs is None:
            object.__setattr__(self, 'edge_attrs', {})
        # Ensure global_attrs is initialized
        if self.global_attrs is None:
            object.__setattr__(self, 'global_attrs', {})
    
    def replace(self, **kwargs) -> 'GraphState':
        """
        Create a new graph state with updated components.
        
        This is the primary way to "modify" the graph, following
        JAX's immutability approach.
        """
        return dataclasses.replace(self, **kwargs)
    
    @property
    def num_nodes(self) -> int:
        """
        Get the number of active nodes in the graph.

        In capacity mode, counts only active nodes (node_type >= 0).
        In dynamic mode, returns total array size.
        """
        if self.is_capacity_mode:
            return int(jnp.sum(self.node_types >= 0))
        if not self.node_attrs:
            return 0
        return next(iter(self.node_attrs.values())).shape[0]

    @property
    def is_capacity_mode(self) -> bool:
        """
        Check if this state is in capacity mode.

        Capacity mode uses fixed-size arrays with inactive slots (node_type=-1).
        Dynamic mode uses dynamically-sized arrays.
        """
        return jnp.any(self.node_types == -1)

    @property
    def capacity(self) -> Optional[int]:
        """
        Get the capacity (max nodes) in capacity mode.

        Returns None if in dynamic mode.
        """
        if self.is_capacity_mode:
            return int(self.node_types.shape[0])
        return None

    def get_active_indices(self) -> jnp.ndarray:
        """
        Get array of indices for active nodes.

        Returns:
            Array of indices where node_type >= 0
        """
        return jnp.where(self.node_types >= 0)[0]

    def get_active_mask(self) -> jnp.ndarray:
        """
        Get boolean mask for active nodes.

        Returns:
            Boolean array: True for active nodes, False for inactive
        """
        return self.node_types >= 0

    def update_node_attrs(self, attr_name: str, new_values: jnp.ndarray) -> 'GraphState':
        """
        Create a new graph with an updated node attribute.
        """
        new_node_attrs = dict(self.node_attrs)
        new_node_attrs[attr_name] = new_values
        return self.replace(node_attrs=new_node_attrs)
    
    def update_adj_matrix(self, rel_name: str, new_matrix: jnp.ndarray) -> 'GraphState':
        """
        Create a new graph with an updated adjacency matrix.
        """
        new_adj_matrices = dict(self.adj_matrices)
        new_adj_matrices[rel_name] = new_matrix
        return self.replace(adj_matrices=new_adj_matrices)
    
    def update_edge_attrs(self, attr_name: str, new_values: jnp.ndarray) -> 'GraphState':
        """
        Create a new graph with an updated edge attribute.
        """
        new_edge_attrs = dict(self.edge_attrs)
        new_edge_attrs[attr_name] = new_values
        return self.replace(edge_attrs=new_edge_attrs)

    def update_global_attr(self, attr_name: str, value: Any) -> 'GraphState':
        """
        Create a new graph with an updated global attribute.
        """
        new_global_attrs = dict(self.global_attrs)
        new_global_attrs[attr_name] = value
        return self.replace(global_attrs=new_global_attrs)

    def tree_flatten(self):
        """
        Flatten GraphState for JAX pytree operations.

        Returns:
            children: List of arrays (the dynamic data JAX can transform)
            aux_data: Tuple of static metadata (dict keys, structure info)
        """
        # Children are the actual arrays that JAX will transform
        children = [self.node_types]

        # Sort keys for deterministic ordering
        node_attr_keys = sorted(self.node_attrs.keys())
        adj_matrix_keys = sorted(self.adj_matrices.keys())
        edge_attr_keys = sorted(self.edge_attrs.keys())

        # Add arrays from dicts
        for k in node_attr_keys:
            children.append(self.node_attrs[k])
        for k in adj_matrix_keys:
            children.append(self.adj_matrices[k])
        for k in edge_attr_keys:
            children.append(self.edge_attrs[k])

        # Auxiliary data: dict keys and global_attrs (static, not traced)
        aux_data = (
            tuple(node_attr_keys),
            tuple(adj_matrix_keys),
            tuple(edge_attr_keys),
            tuple(self.global_attrs.items())  # Treat as static
        )

        return children, aux_data

    @classmethod
    def tree_unflatten(cls, aux_data, children):
        """
        Reconstruct GraphState from flattened pytree.

        Args:
            aux_data: Tuple of static metadata (dict keys, structure info)
            children: List of arrays

        Returns:
            Reconstructed GraphState
        """
        node_attr_keys, adj_matrix_keys, edge_attr_keys, global_items = aux_data

        # First child is always node_types
        node_types = children[0]
        idx = 1

        # Reconstruct node_attrs dict
        node_attrs = {}
        for k in node_attr_keys:
            node_attrs[k] = children[idx]
            idx += 1

        # Reconstruct adj_matrices dict
        adj_matrices = {}
        for k in adj_matrix_keys:
            adj_matrices[k] = children[idx]
            idx += 1

        # Reconstruct edge_attrs dict
        edge_attrs = {}
        for k in edge_attr_keys:
            edge_attrs[k] = children[idx]
            idx += 1

        # Reconstruct global_attrs from static data
        global_attrs = dict(global_items)

        return cls(
            node_types=node_types,
            node_attrs=node_attrs,
            adj_matrices=adj_matrices,
            edge_attrs=edge_attrs,
            global_attrs=global_attrs
        )


def create_padded_state(
    capacity: int,
    initial_active: int,
    node_types_init: Optional[jnp.ndarray] = None,
    node_attrs_init: Optional[Dict[str, jnp.ndarray]] = None,
    adj_matrices_init: Optional[Dict[str, jnp.ndarray]] = None,
    edge_attrs: Optional[Dict[str, jnp.ndarray]] = None,
    global_attrs: Optional[Dict[str, Any]] = None
) -> GraphState:
    """
    Create a GraphState with fixed capacity (padded arrays).

    This enables O(1) add/remove operations via slot activation/deactivation
    instead of array resizing.

    Args:
        capacity: Maximum number of nodes (fixed array size)
        initial_active: Number of initially active nodes
        node_types_init: Initial node types array (length = initial_active)
        node_attrs_init: Dict of initial node attribute arrays (length = initial_active)
        adj_matrices_init: Dict of initial adjacency matrices (shape = initial_active x initial_active)
        edge_attrs: Dict of initial edge attribute arrays (optional)
        global_attrs: Dict of global attributes (optional)

    Returns:
        GraphState with padded arrays (capacity - initial_active inactive slots)

    Raises:
        ValueError: If initial_active > capacity

    Example:
        >>> state = create_padded_state(
        ...     capacity=10,
        ...     initial_active=3,
        ...     node_types_init=jnp.array([0, 0, 0]),
        ...     node_attrs_init={"resources": jnp.array([100.0, 100.0, 100.0])},
        ...     adj_matrices_init={"network": jnp.eye(3)}
        ... )
        >>> state.capacity
        10
        >>> state.num_nodes
        3
    """
    if initial_active > capacity:
        raise ValueError(f"initial_active ({initial_active}) cannot exceed capacity ({capacity})")

    # Create padded node_types array
    # Active nodes: node_type >= 0
    # Inactive slots: node_type = -1
    if node_types_init is None:
        node_types_init = jnp.zeros(initial_active, dtype=jnp.int32)

    padded_node_types = jnp.concatenate([
        node_types_init,
        jnp.full(capacity - initial_active, -1, dtype=jnp.int32)
    ])

    # Pad node attributes
    padded_node_attrs = {}
    if node_attrs_init:
        for key, arr in node_attrs_init.items():
            # Pad with zeros
            padding = jnp.zeros((capacity - initial_active,) + arr.shape[1:], dtype=arr.dtype)
            padded_node_attrs[key] = jnp.concatenate([arr, padding])

    # Pad adjacency matrices
    padded_adj_matrices = {}
    if adj_matrices_init:
        for key, mat in adj_matrices_init.items():
            # Pad to capacity x capacity
            padded_mat = jnp.zeros((capacity, capacity), dtype=mat.dtype)
            padded_mat = padded_mat.at[:initial_active, :initial_active].set(mat)
            padded_adj_matrices[key] = padded_mat

    return GraphState(
        node_types=padded_node_types,
        node_attrs=padded_node_attrs,
        adj_matrices=padded_adj_matrices,
        edge_attrs=edge_attrs or {},
        global_attrs=global_attrs or {}
    )