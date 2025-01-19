<template>
  <div class="about-container">
    <div class="markdown-content" v-html="compiledMarkdown"></div>
  </div>
 </template>
 
 <script>
 import { marked } from 'marked'
 
 export default {
  name: 'About',
  data() {
    return {
      markdown: `# About Airbnb Hosts Study
 
 This project is from my graduate dissertation, which aims to explore the commercialization process of Airbnb from the perspective of Listing Hosts. Currently still being updated.
 
 ## Data Notes
 
 1. The coordinates of the listing are fuzzy. Airbnb uses a circle with a radius of 150m as a fuzzy buffer.
 2. `
    }
  },
  computed: {
    compiledMarkdown() {
      return marked(this.markdown)
    }
  }
 }
 </script>
 
 <style>
 .markdown-content {
  padding: 20px;
  line-height: 1.6;
 }
 
 .markdown-content h1 {
  font-size: 2rem;
  margin-bottom: 1.5rem;
  font-weight: bold;
 }
 
 .markdown-content h2 {
  font-size: 1.5rem;
  margin: 2rem 0 1rem;
  font-weight: bold;
 }
 
 .markdown-content p {
  margin-bottom: 1rem;
 }
 
 .markdown-content ol {
  margin-left: 1.5rem;
  margin-bottom: 1rem;
 }
 
 .markdown-content li {
  margin-bottom: 0.5rem;
 }
 </style>