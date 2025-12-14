/**
 * HMM State View Component
 *
 * Visualizes Hidden Markov Model state transitions
 * - State transition diagram using D3.js
 * - Transition probabilities
 * - Current state highlight
 * - Emission probabilities
 */

import React, { useEffect, useRef, useMemo } from 'react';
import * as d3 from 'd3';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Tabs } from '../ui/tabs';
import type { HMMState } from '../../types/regime';
import { getRegimeDisplayName, getRegimeColor } from '../../types/regime';

export interface HMMStateViewProps {
  hmmState: HMMState;
  transitionMatrix: number[][];
  className?: string;
}

interface Node {
  id: string;
  x: number;
  y: number;
  probability: number;
  color: string;
}

interface Link {
  source: string;
  target: string;
  probability: number;
}

export const HMMStateView: React.FC<HMMStateViewProps> = ({
  hmmState,
  transitionMatrix,
  className = '',
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [activeTab, setActiveTab] = React.useState<'diagram' | 'matrix' | 'emissions'>('diagram');

  const { nodes, links } = useMemo(() => {
    const stateNames = hmmState.transition_matrix.state_names;
    const probabilities = hmmState.state_probabilities;

    // Create nodes in a circle layout
    const nodeCount = stateNames.length;
    const radius = 150;
    const centerX = 250;
    const centerY = 200;

    const nodeList: Node[] = stateNames.map((name, i) => {
      const angle = (i / nodeCount) * 2 * Math.PI - Math.PI / 2;
      return {
        id: name,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        probability: probabilities[name] || 0,
        color: getRegimeColor(name),
      };
    });

    // Create links from transition matrix
    const linkList: Link[] = [];
    transitionMatrix.forEach((row, i) => {
      row.forEach((prob, j) => {
        if (prob > 0.05 && i !== j) {
          // Only show significant transitions
          linkList.push({
            source: stateNames[i],
            target: stateNames[j],
            probability: prob,
          });
        }
      });
    });

    return { nodes: nodeList, links: linkList };
  }, [hmmState, transitionMatrix]);

  useEffect(() => {
    if (!svgRef.current || activeTab !== 'diagram') return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 500;
    const height = 400;

    svg.attr('viewBox', `0 0 ${width} ${height}`);

    // Create arrow markers
    svg
      .append('defs')
      .selectAll('marker')
      .data(['arrow'])
      .enter()
      .append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#6b7280');

    // Draw links
    const linkElements = svg
      .append('g')
      .selectAll('path')
      .data(links)
      .enter()
      .append('path')
      .attr('d', (d) => {
        const sourceNode = nodes.find((n) => n.id === d.source);
        const targetNode = nodes.find((n) => n.id === d.target);

        if (!sourceNode || !targetNode) return '';

        // Calculate control point for curved arrows
        const dx = targetNode.x - sourceNode.x;
        const dy = targetNode.y - sourceNode.y;
        const dr = Math.sqrt(dx * dx + dy * dy);
        const offsetX = -dy * 0.2;
        const offsetY = dx * 0.2;

        return `M${sourceNode.x},${sourceNode.y}Q${sourceNode.x + dx / 2 + offsetX},${sourceNode.y + dy / 2 + offsetY} ${targetNode.x},${targetNode.y}`;
      })
      .attr('fill', 'none')
      .attr('stroke', '#6b7280')
      .attr('stroke-width', (d) => 1 + d.probability * 3)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', 'url(#arrow)');

    // Add link labels
    svg
      .append('g')
      .selectAll('text')
      .data(links)
      .enter()
      .append('text')
      .attr('x', (d) => {
        const sourceNode = nodes.find((n) => n.id === d.source);
        const targetNode = nodes.find((n) => n.id === d.target);
        if (!sourceNode || !targetNode) return 0;
        return (sourceNode.x + targetNode.x) / 2;
      })
      .attr('y', (d) => {
        const sourceNode = nodes.find((n) => n.id === d.source);
        const targetNode = nodes.find((n) => n.id === d.target);
        if (!sourceNode || !targetNode) return 0;
        return (sourceNode.y + targetNode.y) / 2;
      })
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#6b7280')
      .text((d) => (d.probability * 100).toFixed(0) + '%');

    // Draw nodes
    const nodeElements = svg
      .append('g')
      .selectAll('circle')
      .data(nodes)
      .enter()
      .append('circle')
      .attr('cx', (d) => d.x)
      .attr('cy', (d) => d.y)
      .attr('r', (d) => 20 + d.probability * 20)
      .attr('fill', (d) => d.color)
      .attr('stroke', (d) =>
        d.id === hmmState.current_state ? '#1f2937' : 'white'
      )
      .attr('stroke-width', (d) =>
        d.id === hmmState.current_state ? 4 : 2
      )
      .attr('opacity', 0.8);

    // Add node labels
    svg
      .append('g')
      .selectAll('text')
      .data(nodes)
      .enter()
      .append('text')
      .attr('x', (d) => d.x)
      .attr('y', (d) => d.y - 35)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('font-weight', (d) =>
        d.id === hmmState.current_state ? 'bold' : 'normal'
      )
      .attr('fill', '#1f2937')
      .attr('class', 'dark:fill-white')
      .text((d) => getRegimeDisplayName(d.id));

    // Add probability labels
    svg
      .append('g')
      .selectAll('text.prob')
      .data(nodes)
      .enter()
      .append('text')
      .attr('x', (d) => d.x)
      .attr('y', (d) => d.y + 5)
      .attr('text-anchor', 'middle')
      .attr('font-size', '11px')
      .attr('font-weight', 'bold')
      .attr('fill', 'white')
      .text((d) => (d.probability * 100).toFixed(0) + '%');
  }, [nodes, links, hmmState, activeTab]);

  return (
    <Card
      className={`bg-white dark:bg-gray-800 ${className}`}
      role="article"
      aria-label="Hidden Markov Model State View"
    >
      <CardHeader title="HMM State Visualization" />

      <CardBody>
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as 'diagram' | 'matrix' | 'emissions')}
        >
          <Tabs.List>
            <Tabs.Trigger value="diagram">State Diagram</Tabs.Trigger>
            <Tabs.Trigger value="matrix">Transition Matrix</Tabs.Trigger>
            <Tabs.Trigger value="emissions">Emission Probabilities</Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="diagram">
            <div className="py-6">
              <svg
                ref={svgRef}
                className="w-full h-auto max-w-full mx-auto"
                style={{ maxHeight: '400px' }}
                aria-label="State transition diagram"
              />
              <div className="mt-4 text-sm text-gray-600 dark:text-gray-400 text-center">
                <p>
                  Circle size represents state probability. Highlighted border
                  indicates current state.
                </p>
                <p className="mt-1">
                  Arrow thickness represents transition probability.
                </p>
              </div>
            </div>
          </Tabs.Content>

          <Tabs.Content value="matrix">
            <div className="overflow-x-auto py-6">
              <table className="min-w-full border-collapse">
                <thead>
                  <tr>
                    <th className="border border-gray-300 dark:border-gray-600 px-4 py-2 bg-gray-50 dark:bg-gray-900 text-xs font-medium text-gray-500 dark:text-gray-400">
                      From / To
                    </th>
                    {hmmState.transition_matrix.state_names.map((name) => (
                      <th
                        key={name}
                        className="border border-gray-300 dark:border-gray-600 px-4 py-2 bg-gray-50 dark:bg-gray-900 text-xs font-medium text-gray-500 dark:text-gray-400"
                      >
                        {getRegimeDisplayName(name)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {transitionMatrix.map((row, i) => (
                    <tr key={i}>
                      <td className="border border-gray-300 dark:border-gray-600 px-4 py-2 bg-gray-50 dark:bg-gray-900 text-sm font-medium text-gray-900 dark:text-white">
                        {getRegimeDisplayName(
                          hmmState.transition_matrix.state_names[i]
                        )}
                      </td>
                      {row.map((prob, j) => (
                        <td
                          key={j}
                          className="border border-gray-300 dark:border-gray-600 px-4 py-2 text-center text-sm font-mono"
                          style={{
                            backgroundColor: `rgba(59, 130, 246, ${prob * 0.8})`,
                          }}
                        >
                          {(prob * 100).toFixed(1)}%
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                <p>
                  Transition probabilities from row state to column state.
                  Higher values indicate more likely transitions.
                </p>
              </div>
            </div>
          </Tabs.Content>

          <Tabs.Content value="emissions">
            <div className="py-6 space-y-4">
              {Object.entries(hmmState.emission_probabilities).map(
                ([regime, probabilities]) => (
                  <div key={regime} className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <div
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: getRegimeColor(regime) }}
                        aria-hidden="true"
                      />
                      <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                        {getRegimeDisplayName(regime)}
                      </h4>
                    </div>
                    <div className="grid grid-cols-9 gap-1">
                      {probabilities.map((prob, idx) => (
                        <div
                          key={idx}
                          className="text-center p-2 rounded border border-gray-200 dark:border-gray-700"
                          style={{
                            backgroundColor: `rgba(59, 130, 246, ${prob})`,
                          }}
                          title={`Observation ${idx}: ${(prob * 100).toFixed(1)}%`}
                        >
                          <div className="text-xs font-mono text-gray-900 dark:text-white">
                            {(prob * 100).toFixed(0)}%
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              )}
              <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                <p>
                  Emission probabilities show the likelihood of observing each
                  discretized market signal given the regime state.
                </p>
              </div>
            </div>
          </Tabs.Content>
        </Tabs>
      </CardBody>
    </Card>
  );
};
