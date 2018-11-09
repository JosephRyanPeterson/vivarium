(ns shepherd.core
  (:require
   [manifold.deferred :as defer]
   [taoensso.timbre :as log]
   [flow.core :as flow]
   [shepherd.process :as process]
   [shepherd.agent :as agent]))

(defn add-agent
  [state message]
  (log/info "add agent:" message)
  (let [record (select-keys message [:id :type :config])
        born (agent/launch-agent message (:agent-dir state))
        record (assoc record :agent born)]
    (swap! (:agents state) assoc (:id record) record)
    (log/info "new agent" record)
    (process/stream-out (:agent record))))

(defn handle-message
  [state topic message]
  (condp = (:event message)
    "ADD_AGENT"
    (add-agent state message)))

(defn boot
  [config]
  (let [agents (atom {})
        state (assoc config :agents agents)
        handle (partial handle-message state)]
    (assoc-in state [:kafka :handle-message] handle)))

(defn -main
  [& args]
  (let [config (flow/read-config "config/config.clj")
        state (boot config)]
    (log/info "shepherd starting" (:port config))
    (log/info state)
    (flow/start state)))
