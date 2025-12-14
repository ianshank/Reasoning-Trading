/**
 * MCTS Tree Visualization Component
 *
 * Interactive force-directed graph visualization of the MCTS tree
 * using D3.js for layout and rendering.
 */

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import type { MCTSTree, MCTSNode } from '../../types/mcts';

/**
 * Node data for D3 visualization
 */
interface D3Node extends d3.SimulationNodeDatum {
  id: string;
  data: MCTSNode;
  level: number;
  isSelected: boolean;
  isOnBestPath: boolean;
  isExpanded: boolean;
}

/**
 * Link data for D3 visualization
 */
interface D3Link extends d3.SimulationLinkDatum<D3Node> {
  source: D3Node;
  target: D3Node;
  value: number;
}

/**
 * Hierarchy level filter type
 */
export type HierarchyLevel = 'strategic' | 'tactical' | 'execution' | 'all';

/**
 * MCTSTree component props
 */
export interface MCTSTreeProps {
  /**
   * MCTS tree data to visualize
   */
  treeData: MCTSTree | null;

  /**
   * Callback when a node is clicked
   */
  onNodeClick?: (nodeId: string) => void;

  /**
   * Currently selected node ID
   */
  selectedNodeId?: string | null;

  /**
   * Path to highlight (array of node IDs)
   */
  highlightPath?: string[];

  /**
   * Hierarchy level filter
   * @default 'all'
   */
  levelFilter?: HierarchyLevel;

  /**
   * Width of the visualization
   * @default 800
   */
  width?: number;

  /**
   * Height of the visualization
   * @default 600
   */
  height?: number;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get color based on Q-value
 */
function getNodeColor(qValue: number): string {
  // Q-value typically ranges from -3 to 3 (Sharpe ratio scale)
  // Map to color: red (bad) -> yellow (neutral) -> green (good)
  const normalized = Math.max(-3, Math.min(3, qValue));
  const scaled = (normalized + 3) / 6; // 0 to 1

  if (scaled < 0.5) {
    // Red to yellow
    const ratio = scaled * 2;
    return d3.interpolateRgb('#ef4444', '#fbbf24')(ratio);
  } else {
    // Yellow to green
    const ratio = (scaled - 0.5) * 2;
    return d3.interpolateRgb('#fbbf24', '#22c55e')(ratio);
  }
}

/**
 * Get node radius based on visit count
 */
function getNodeRadius(visits: number, maxVisits: number): number {
  const minRadius = 4;
  const maxRadius = 20;
  if (maxVisits === 0) return minRadius;
  const normalized = Math.sqrt(visits / maxVisits);
  return minRadius + normalized * (maxRadius - minRadius);
}

/**
 * Determine hierarchy level from node depth
 */
function getHierarchyLevel(depth: number): HierarchyLevel {
  if (depth <= 1) return 'strategic';
  if (depth <= 3) return 'tactical';
  return 'execution';
}

/**
 * MCTS Tree visualization with interactive force-directed layout
 *
 * Features:
 * - Force-directed graph layout using D3.js
 * - Node sizing based on visit count
 * - Color coding based on Q-value
 * - Click to expand/collapse subtrees
 * - Hover tooltips with node details
 * - Zoom and pan controls
 * - Level filtering (Strategic/Tactical/Execution)
 *
 * @example
 * ```tsx
 * <MCTSTree
 *   treeData={tree}
 *   onNodeClick={(id) => console.log('Clicked:', id)}
 *   selectedNodeId={selectedId}
 *   highlightPath={bestPath}
 *   levelFilter="tactical"
 * />
 * ```
 */
export const MCTSTree: React.FC<MCTSTreeProps> = ({
  treeData,
  onNodeClick,
  selectedNodeId = null,
  highlightPath = [],
  levelFilter = 'all',
  width = 800,
  height = 600,
  className = '',
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!treeData || !svgRef.current) return;

    // Clear previous visualization
    d3.select(svgRef.current).selectAll('*').remove();

    // Create SVG container
    const svg = d3
      .select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);

    // Add zoom behavior
    const g = svg.append('g');
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    svg.call(zoom);

    // Convert tree to D3 format
    const nodes: D3Node[] = [];
    const links: D3Link[] = [];
    const nodeMap = new Map<string, D3Node>();

    // Calculate max visits for scaling
    const maxVisits = Math.max(
      ...Object.values(treeData.nodes).map((n) => n.visits)
    );

    // Build nodes
    const buildNode = (node: MCTSNode, level: number, parent: D3Node | null) => {
      const hierarchyLevel = getHierarchyLevel(level);

      // Check level filter
      if (levelFilter !== 'all' && hierarchyLevel !== levelFilter) {
        return;
      }

      const d3Node: D3Node = {
        id: node.id,
        data: node,
        level,
        isSelected: node.id === selectedNodeId,
        isOnBestPath: highlightPath.includes(node.id),
        isExpanded: expandedNodes.has(node.id) || level === 0,
      };

      nodes.push(d3Node);
      nodeMap.set(node.id, d3Node);

      // Add link to parent
      if (parent) {
        links.push({
          source: parent,
          target: d3Node,
          value: node.visits,
        });
      }

      // Recursively build children if expanded
      if (d3Node.isExpanded && node.children_ids.length > 0) {
        node.children_ids.forEach((childId) => {
          const childNode = treeData.nodes[childId];
          if (childNode) {
            buildNode(childNode, level + 1, d3Node);
          }
        });
      }
    };

    buildNode(treeData.root, 0, null);

    // Create force simulation
    const simulation = d3
      .forceSimulation(nodes)
      .force(
        'link',
        d3
          .forceLink<D3Node, D3Link>(links)
          .id((d) => d.id)
          .distance(80)
          .strength(1)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    // Create link elements
    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll<SVGLineElement, D3Link>('line')
      .data(links)
      .join('line')
      .attr('stroke', '#94a3b8')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', (d) => Math.sqrt(d.value) * 0.5);

    // Create node groups
    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll<SVGGElement, D3Node>('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation();
        if (onNodeClick) {
          onNodeClick(d.id);
        }
        // Toggle expansion
        setExpandedNodes((prev) => {
          const next = new Set(prev);
          if (next.has(d.id)) {
            next.delete(d.id);
          } else {
            next.add(d.id);
          }
          return next;
        });
      });

    // Add circles to nodes
    node
      .append('circle')
      .attr('r', (d) => getNodeRadius(d.data.visits, maxVisits))
      .attr('fill', (d) => {
        if (d.isSelected) return '#3b82f6';
        if (d.isOnBestPath) return '#8b5cf6';
        return getNodeColor(d.data.q_value);
      })
      .attr('stroke', (d) => (d.isOnBestPath ? '#6d28d9' : '#fff'))
      .attr('stroke-width', (d) => (d.isOnBestPath ? 3 : 1.5))
      .attr('opacity', 0.9);

    // Add expand/collapse indicator
    node
      .filter((d) => d.data.children_ids.length > 0)
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', '#fff')
      .attr('font-size', '10px')
      .attr('pointer-events', 'none')
      .text((d) => (d.isExpanded ? '−' : '+'));

    // Create tooltip
    const tooltip = d3
      .select('body')
      .append('div')
      .attr('class', 'mcts-tooltip')
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background-color', 'rgba(0, 0, 0, 0.8)')
      .style('color', '#fff')
      .style('padding', '8px 12px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('z-index', '1000');

    // Add tooltip behavior
    node
      .on('mouseenter', (event, d) => {
        const actionStr = d.data.action
          ? `${d.data.action.direction} (${(d.data.action.position_size.size_fraction * 100).toFixed(1)}%)`
          : 'Root';

        tooltip
          .style('visibility', 'visible')
          .html(`
            <div>
              <strong>Action:</strong> ${actionStr}<br/>
              <strong>Visits:</strong> ${d.data.visits}<br/>
              <strong>Q-value:</strong> ${d.data.q_value.toFixed(3)}<br/>
              <strong>Prior:</strong> ${(d.data.prior * 100).toFixed(1)}%<br/>
              <strong>Depth:</strong> ${d.data.depth}<br/>
              ${d.data.is_terminal ? '<strong>Terminal Node</strong>' : ''}
            </div>
          `);
      })
      .on('mousemove', (event) => {
        tooltip
          .style('top', event.pageY - 10 + 'px')
          .style('left', event.pageX + 10 + 'px');
      })
      .on('mouseleave', () => {
        tooltip.style('visibility', 'hidden');
      });

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as D3Node).x ?? 0)
        .attr('y1', (d) => (d.source as D3Node).y ?? 0)
        .attr('x2', (d) => (d.target as D3Node).x ?? 0)
        .attr('y2', (d) => (d.target as D3Node).y ?? 0);

      node.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    // Cleanup
    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [
    treeData,
    selectedNodeId,
    highlightPath,
    expandedNodes,
    levelFilter,
    width,
    height,
    onNodeClick,
  ]);

  if (!treeData) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <p className="text-gray-500 dark:text-gray-400">No tree data available</p>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <svg
        ref={svgRef}
        className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900"
        role="img"
        aria-label="MCTS tree visualization"
      />
      <div className="absolute top-4 right-4 bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-semibold mb-2 text-gray-900 dark:text-gray-100">
          Legend
        </h4>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-gray-700 dark:text-gray-300">Low Q-value</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-gray-700 dark:text-gray-300">Medium Q-value</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-gray-700 dark:text-gray-300">High Q-value</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500 border-2 border-blue-700" />
            <span className="text-gray-700 dark:text-gray-300">Selected</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500 border-2 border-purple-700" />
            <span className="text-gray-700 dark:text-gray-300">Best Path</span>
          </div>
        </div>
      </div>
    </div>
  );
};

MCTSTree.displayName = 'MCTSTree';
